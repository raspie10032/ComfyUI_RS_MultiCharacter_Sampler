# Adapted from ostris/ComfyUI-Krea2-Ostris-Edit, MIT.
# Source revision 7756566160c4a1b24bb1bd9f0ff3ced1a83d7547. See KREA2-POSE-LICENSE.
"""Execution-scoped reference K/V for the Krea2 Turbo pose LoRA."""
import torch
import torch.nn.functional as F
from einops import rearrange
import comfy.ldm.common_dit
import comfy.utils
from comfy.ldm.flux.layers import timestep_embedding
from comfy.ldm.flux.math import apply_rope
from comfy.ldm.modules.attention import optimized_attention_masked

def _pack_refs(dit, ref_latents, bs, device, dtype):
    """Patchify reference latents into tokens + RoPE positions: each reference
    gets axis-0 index i+1 with its own y/x grid from 0. Returns
    ``(reftok (B, Lr, C*p*p), refpos (B, Lr, 3))``."""
    patch = dit.patch
    ref_tokens = []
    ref_pos = []
    for i, ref in enumerate(ref_latents):
        if ref.ndim == 5:  # (B, C, T, H, W) Wan21 layout, T == 1 for images
            rb, rc, rt, rh5, rw5 = ref.shape
            ref = ref.reshape(rb * rt, rc, rh5, rw5)
        ref = comfy.ldm.common_dit.pad_to_patch_size(
            ref.to(device, dtype), (patch, patch)
        )
        ref = comfy.utils.repeat_to_batch_size(ref, bs)
        rh, rw = ref.shape[-2] // patch, ref.shape[-1] // patch
        ref_tokens.append(
            rearrange(ref, "b c (h ph) (w pw) -> b (h w) (c ph pw)", ph=patch, pw=patch)
        )
        rid = torch.zeros(rh, rw, 3, device=device, dtype=torch.float32)
        rid[..., 0] = i + 1.0
        rid[..., 1] = torch.arange(rh, device=device, dtype=torch.float32)[:, None]
        rid[..., 2] = torch.arange(rw, device=device, dtype=torch.float32)[None, :]
        ref_pos.append(rid.reshape(1, rh * rw, 3).repeat(bs, 1, 1))
    return torch.cat(ref_tokens, dim=1), torch.cat(ref_pos, dim=1)

def _attn_kv(attn, x, freqs, mask=None, kv_capture=None, kv_cache=None,
             transformer_options={}):
    """comfy krea2 ``Attention.forward`` with optional K/V capture or cached-K/V
    injection. Both happen post-RoPE and pre-GQA-expansion."""
    q, k, v, gate = attn.wq(x), attn.wk(x), attn.wv(x), attn.gate(x)
    q = rearrange(q, "B L (H D) -> B H L D", H=attn.heads)
    k = rearrange(k, "B L (H D) -> B H L D", H=attn.kvheads)
    v = rearrange(v, "B L (H D) -> B H L D", H=attn.kvheads)
    q, k = attn.qknorm(q, k)
    if freqs is not None:
        q, k = apply_rope(q, k, freqs)
    if kv_capture is not None:
        kv_capture.append((k, v))
    if kv_cache is not None:
        # Cached ref K/V are already RoPE'd at their original positions.
        k = torch.cat((k, kv_cache[0].to(k.dtype)), dim=2)
        v = torch.cat((v, kv_cache[1].to(v.dtype)), dim=2)
    if attn.kvheads != attn.heads:
        rep = attn.heads // attn.kvheads
        k = k.repeat_interleave(rep, dim=1)
        v = v.repeat_interleave(rep, dim=1)
    out = optimized_attention_masked(q, k, v, attn.heads, mask=mask,
                                     skip_reshape=True,
                                     transformer_options=transformer_options)
    return attn.wo(out * F.sigmoid(gate))

def _block_kv_forward(block, x, vec, freqs, kv_capture=None, kv_cache=None,
                      transformer_options={}):
    """SingleStreamBlock forward (single-span modulation) with K/V capture /
    injection in the attention."""
    prescale, preshift, pregate, postscale, postshift, postgate = block.mod(vec)
    x = x + pregate * _attn_kv(
        block.attn, (1 + prescale) * block.prenorm(x) + preshift, freqs,
        kv_capture=kv_capture, kv_cache=kv_cache,
        transformer_options=transformer_options,
    )
    x = x + postgate * block.mlp((1 + postscale) * block.postnorm(x) + postshift)
    return x

def _precompute_ref_kv(dit, x, timesteps, ref_latents, transformer_options):
    """Run only the clean reference tokens through the blocks at t=0 and record
    each block's post-RoPE K/V.

    An isolate-ref-attention LoRA never lets ref tokens see the text / noisy
    tokens, so this standalone pass produces exactly the K/V the refs would
    contribute inside a joint pass -- and they are timestep-invariant, so one
    pass serves the whole denoise."""
    bs = x.shape[0] * (x.shape[2] if x.ndim == 5 else 1)
    reftok, refpos = _pack_refs(dit, ref_latents, bs, x.device, x.dtype)
    h = dit.first(reftok)
    t0 = dit.tmlp(
        timestep_embedding(torch.zeros_like(timesteps), dit.tdim)
        .unsqueeze(1)
        .to(h.dtype)
    )
    tvec0 = dit.tproj(t0)
    freqs = dit.pe_embedder(refpos)

    ref_kv = []
    for block in dit.blocks:
        cap = []
        h = _block_kv_forward(
            block, h, tvec0, freqs, kv_capture=cap,
            transformer_options=transformer_options,
        )
        ref_kv.append(cap[0])
    return ref_kv

def _forward_with_cached_refs(self, x, timesteps, context, ref_kv, transformer_options):
    """Denoising pass with the reference tokens replaced by their cached K/V:
    the live sequence is just text + noisy image tokens, and every block's
    attention appends the cached ref K/V as extra keys. Matches the joint pass
    of an isolate-ref-attention LoRA without recomputing the refs each step."""
    temporal = x.ndim == 5
    if temporal:
        b5, c5, t5, h5, w5 = x.shape
        x = x.reshape(b5 * t5, c5, h5, w5)
    bs, c, H_orig, W_orig = x.shape
    patch = self.patch
    x = comfy.ldm.common_dit.pad_to_patch_size(x, (patch, patch))
    H, W = x.shape[-2], x.shape[-1]
    h_, w_ = H // patch, W // patch
    device = x.device

    context = self._unpack_context(context)

    img = self.first(
        rearrange(x, "b c (h ph) (w pw) -> b (h w) (c ph pw)", ph=patch, pw=patch)
    )

    t = self.tmlp(timestep_embedding(timesteps, self.tdim).unsqueeze(1).to(img.dtype))
    tvec = self.tproj(t)

    context = self.txtfusion(
        context, mask=None, transformer_options=transformer_options
    )
    context = self.txtmlp(context)

    txtlen, imglen = context.shape[1], img.shape[1]
    combined = torch.cat((context, img), dim=1)

    txtpos = torch.zeros(bs, txtlen, 3, device=device, dtype=torch.float32)
    imgids = torch.zeros(h_, w_, 3, device=device, dtype=torch.float32)
    imgids[..., 1] = torch.arange(h_, device=device, dtype=torch.float32)[:, None]
    imgids[..., 2] = torch.arange(w_, device=device, dtype=torch.float32)[None, :]
    imgpos = imgids.reshape(1, h_ * w_, 3).repeat(bs, 1, 1)
    pos = torch.cat((txtpos, imgpos), dim=1)

    freqs = self.pe_embedder(pos)

    transformer_options = transformer_options.copy()
    for index, (block, kv) in enumerate(zip(self.blocks, ref_kv)):
        transformer_options["block_index"] = index
        combined = _block_kv_forward(
            block, combined, tvec, freqs, kv_cache=kv,
            transformer_options=transformer_options,
        )

    final = self.last(combined, t)
    out = final[:, txtlen : txtlen + imglen, :]
    out = rearrange(
        out,
        "b (h w) (c ph pw) -> b c (h ph) (w pw)",
        h=h_,
        w=w_,
        ph=patch,
        pw=patch,
        c=self.channels,
    )
    out = out[:, :, :H_orig, :W_orig]
    if temporal:
        out = out.reshape(b5, t5, self.channels, H_orig, W_orig).movedim(1, 2)
    return out
