# SPDX-License-Identifier: Apache-2.0
# Adapted from AnticPan/Anima-Role-Ref-KV, revision 259a0dce.
# Changes: inference engine only; interruption checks between transformer blocks.
# See ANIMA-ROLE-KV-CODE-LICENSE and docs/anima-role-kv.md.
"""Anima Role Ref KV inference on native ComfyUI Anima components.

Supports single-image inference with BF16 or FP32 Anima Base v1.0.
Adapter weights remain in FP32; the shared base model is not patched.
"""
import torch
import torch.nn.functional as F

TARGETS = ("self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj",
           "self_attn.output_proj", "mlp.layer1", "mlp.layer2")


class NativeEngine:
    def __init__(self, net, weights, strength=1., device=None):
        self.net, self.weights, self.strength = net, weights, strength
        expected = {f"diffusion_model.blocks.{b}.{t}.{s}" for b in range(len(net.blocks))
                    for t in TARGETS for s in ("lora_down.weight", "lora_up.weight", "alpha")}
        if set(weights) != expected:
            raise ValueError("Incomplete Anima Role Ref KV ComfyUI adapter")
        for b in range(len(net.blocks)):
            for t in TARGETS:
                root = f"diffusion_model.blocks.{b}.{t}."
                a, z = weights[root + "lora_down.weight"], weights[root + "lora_up.weight"]
                m = net.blocks[b]
                for part in t.split("."):
                    m = getattr(m, part)
                if a.shape != (128, m.in_features) or z.shape != (m.out_features, 128):
                    raise ValueError(f"Shape mismatch: {root}")
                if float(weights[root + "alpha"]) != 128 or a.dtype != torch.float32 or z.dtype != torch.float32:
                    raise ValueError(f"Unsupported rank/alpha/dtype: {root}")
                if not torch.isfinite(a).all() or not torch.isfinite(z).all():
                    raise ValueError(f"Non-finite adapter: {root}")
        device = next(net.parameters()).device if device is None else torch.device(device)
        self.weights = {k: v.to(device) for k, v in weights.items()}

    @staticmethod
    def rms(module, x, eps=None):
        # Match the Diffusers runtime's FP32 reduction and rounding order. Native
        # torch.rms_norm uses different BF16 rounding, which compounds over blocks.
        variance = x.float().pow(2).mean(-1, keepdim=True)
        h = x * torch.rsqrt(variance + (module.eps if eps is None else eps))
        weight = module.weight.to(x.device)
        return h.to(weight.dtype) * weight

    def linear(self, module, x, block, name):
        y = module(x)
        if self.strength == 0:
            return y
        root = f"diffusion_model.blocks.{block}.{name}."
        a = self.weights[root + "lora_down.weight"].to(x.device)
        b = self.weights[root + "lora_up.weight"].to(x.device)
        delta = (x.to(a.dtype) @ a.t()) @ b.t()
        return y + self.strength * delta.to(y.dtype)

    def rope(self, height, width, target_hw=None, device=None):
        r = self.net.pos_embedder
        device = next(self.net.parameters()).device if device is None else device
        hs, ws = torch.arange(height, device=device), torch.arange(width, device=device)
        if target_hw is not None:
            hs = hs + target_hw[0] // 2 - height // 2
            ws = ws + target_hw[1] // 2 - width // 2
        spatial = r.dim_spatial_range.to(device)
        temporal = r.dim_temporal_range.to(device)
        if target_hw is not None:
            # Reference positions in the Diffusers runtime construct these ranges
            # on the execution device. CPU-precomputed fractions differ by one
            # FP32 ULP on CUDA and can compound through a BF16 reference stream.
            dim_h = self.net.model_channels // self.net.num_heads // 6 * 2
            dim_t = self.net.model_channels // self.net.num_heads - 2 * dim_h
            spatial = torch.arange(0, dim_h, 2, device=device, dtype=torch.float32)[:dim_h // 2] / dim_h
            temporal = torch.arange(0, dim_t, 2, device=device, dtype=torch.float32)[:dim_t // 2] / dim_t
        ts = torch.tensor([0. if target_hw is None else 10.], device=device)
        ft = torch.outer(ts, 1.0 / (10000 * r.t_ntk_factor) ** temporal)[:, None, None].expand(1, height, width, -1)
        fh = torch.outer(hs.float(), 1.0 / (10000 * r.h_ntk_factor) ** spatial)[None, :, None].expand(1, height, width, -1)
        fw = torch.outer(ws.float(), 1.0 / (10000 * r.w_ntk_factor) ** spatial)[None, None].expand(1, height, width, -1)
        angle = torch.cat([ft, fh, fw] * 2, -1).flatten(0, 2)
        return angle.cos(), angle.sin()

    @staticmethod
    def rotate(x, rope):
        a, b = x.reshape(*x.shape[:-1], 2, -1).unbind(-2)
        rotated = torch.cat([-b, a], dim=-1)
        return (x.float() * rope[0][None, None] + rotated.float() * rope[1][None, None]).to(x.dtype)

    def tokens(self, x):
        return self.net.x_embedder(torch.cat([x, torch.zeros_like(x[:, :1])], 1)).flatten(1, 3)

    def time(self, sigma, dtype):
        e, t = self.net.t_embedder[1](self.net.t_embedder[0](sigma[:, None]).to(dtype))
        return self.rms(self.net.t_embedding_norm, e), t

    @staticmethod
    def norm(block, h, e, t, name):
        shift, scale, gate = (getattr(block, "adaln_modulation_" + name)(e) + t).chunk(3, -1)
        n = getattr(block, "layer_norm_" + name)(h)
        return n * (1 + scale) + shift, gate

    def qkv(self, attn, x, i, rope):
        q, k, v = [self.linear(getattr(attn, p + "_proj"), x, i, "self_attn." + p + "_proj")
                   .unflatten(-1, (attn.n_heads, -1)).transpose(1, 2) for p in ("q", "k", "v")]
        # The supported Diffusers Cosmos Attention uses eps=1e-5;
        # ComfyUI's Anima defaults to 1e-6. Use the same value in both runtimes.
        return self.rotate(self.rms(attn.q_norm, q, 1e-5), rope), self.rotate(self.rms(attn.k_norm, k, 1e-5), rope), v

    def block(self, block, h, ctx, e, t, rope, i, ref=None, cache_only=False):
        n, gate = self.norm(block, h, e, t, "self_attn")
        q, k, v = self.qkv(block.self_attn, n, i, rope)
        own = (k, v)
        if cache_only:
            return h, own
        if ref is not None:
            k, v = torch.cat([ref[0], k], 2), torch.cat([ref[1], v], 2)
        o = F.scaled_dot_product_attention(q, k, v).transpose(1, 2).flatten(2)
        h = h + gate * self.linear(block.self_attn.output_proj, o, i, "self_attn.output_proj")
        n, gate = self.norm(block, h, e, t, "cross_attn")
        a = block.cross_attn
        q = self.rms(a.q_norm, a.q_proj(n).unflatten(-1, (a.n_heads, -1)).transpose(1, 2), 1e-5)
        k = self.rms(a.k_norm, a.k_proj(ctx).unflatten(-1, (a.n_heads, -1)).transpose(1, 2), 1e-5)
        v = a.v_proj(ctx).unflatten(-1, (a.n_heads, -1)).transpose(1, 2)
        h = h + gate * a.output_proj(F.scaled_dot_product_attention(q, k, v).transpose(1, 2).flatten(2))
        n, gate = self.norm(block, h, e, t, "mlp")
        o = block.mlp.activation(self.linear(block.mlp.layer1, n, i, "mlp.layer1"))
        return h + gate * self.linear(block.mlp.layer2, o, i, "mlp.layer2"), own

    def reference(self, ref, ctx, target_hw):
        h = self.tokens(ref)
        e, t = self.time(torch.zeros(1, device=ref.device), h.dtype)
        rope = self.rope(ref.shape[-2] // 2, ref.shape[-1] // 2,
                         (target_hw[0] // 2, target_hw[1] // 2), device=ref.device)
        cache = []
        from .runtime_control import check_interrupted
        for i, block in enumerate(self.net.blocks):
            check_interrupted()
            h, kv = self.block(block, h, ctx, e, t, rope, i, cache_only=i == len(self.net.blocks) - 1)
            cache.append(kv)
        return cache

    def velocity(self, x, sigma, ctx, cache=None):
        h = self.tokens(x)
        e, t = self.time(sigma, h.dtype)
        hp, wp = x.shape[-2] // 2, x.shape[-1] // 2
        rope = self.rope(hp, wp, device=x.device)
        from .runtime_control import check_interrupted
        for i, block in enumerate(self.net.blocks):
            check_interrupted()
            h, _ = self.block(block, h, ctx, e, t, rope, i, None if cache is None else cache[i])
        h = self.net.final_layer(h.reshape(x.shape[0], 1, hp, wp, -1), e, t)
        return self.net.unpatchify(h).float()

