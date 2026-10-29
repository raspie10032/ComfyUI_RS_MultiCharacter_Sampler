# SPDX-License-Identifier: GPL-3.0-only
"""Experimental asymmetric Anima 2B reference, with sample-local K/V banks.

Block/frame math adapted from ElectronGirl/ComfyUI-Anima-Ref-Adapter
bd1e094a (Apache-2.0, see ANIMA-REF-ADAPTER-LICENSE). Released weights separate.
The reference prefill is independent of RS target attention and text routing.
"""
import hashlib
import time

import torch

from .anima_ref_frame import FrameRuntime, frame_rope
from .routing import sdpa


def block_mods(block, emb, adaln):
    result=[]
    for modulation in (block.adaln_modulation_self_attn,block.adaln_modulation_cross_attn,block.adaln_modulation_mlp):
        m=modulation(emb)+adaln if block.use_adaln_lora else modulation(emb)
        result.append(tuple(t[:,:,None,None,:] for t in m.chunk(3,dim=-1)))
    return result


def norm(x,layer,scale,shift):
    return layer(x)*(1+scale)+shift


def frame_embed(dm,latent,sigma,reference=False,target_grid=None):
    value,_,_=dm.prepare_embedded_sequence(latent,fps=None,padding_mask=None)
    _,_,h,w,_=value.shape
    if reference:
        th,_=target_grid
        # Native v2 shift, without stretching the reference's spatial axes.
        hh,ww=torch.meshgrid(torch.arange(h,device=latent.device)+th,torch.arange(w,device=latent.device),indexing='ij')
        positions=(torch.ones(h*w,device=latent.device),hh.flatten(),ww.flatten())
        pieces=[]
        pe=dm.pos_embedder
        for pos,factor,span in zip(positions,(pe.t_ntk_factor,pe.h_ntk_factor,pe.w_ntk_factor),(pe.dim_temporal_range,pe.dim_spatial_range,pe.dim_spatial_range)):
            angles=torch.outer(pos.float(),1./((10000.*factor)**span.to(latent.device)))
            pieces.append(torch.stack((angles.cos(),-angles.sin(),angles.sin(),angles.cos()),-1))
        rope=torch.cat(pieces,-2);rope=rope.reshape(*rope.shape[:-1],2,2).float()
    else:
        rope=frame_rope(dm.pos_embedder,h,w,latent.device,0)
    emb,adaln=dm.t_embedder[1](dm.t_embedder[0](sigma.reshape(-1,1).float()).to(value.dtype))
    if value.dtype==torch.float16:value=value.float()
    return value,rope[None,:,None],dm.t_embedding_norm(emb),adaln


def asym_block(block,value,emb,adaln,rope,context=None,ref_kv=None,options=None):
    sa,ca,mlp=block_mods(block,emb,adaln)
    residual_dtype,compute_dtype=value.dtype,emb.dtype
    B,T,H,W,_=value.shape
    n=norm(value,block.layer_norm_self_attn,sa[1],sa[0]).to(compute_dtype).flatten(1,3)
    q,k,v=block.self_attn.compute_qkv(n,None,rope_emb=rope)
    own=(k,v)
    if context is None:
        # No RS masks, text conditions, or live target features in prefill.
        out=block.self_attn.output_dropout(block.self_attn.output_proj(sdpa(q,k,v)))
    else:
        kr,vr=ref_kv
        if kr.shape[0]!=B:kr,vr=kr.expand(B,*kr.shape[1:]),vr.expand(B,*vr.shape[1:])
        k,v=torch.cat((k,kr.to(k)),1),torch.cat((v,vr.to(v)),1)
        out=block.self_attn.compute_attention(q,k,v,transformer_options=options)
    value=torch.addcmul(value,sa[2].to(residual_dtype),out.reshape(B,T,H,W,-1).to(residual_dtype))
    if context is not None:
        n=norm(value,block.layer_norm_cross_attn,ca[1],ca[0]).to(compute_dtype).flatten(1,3)
        out=block.cross_attn(n,context,rope_emb=None,transformer_options=options).reshape(B,T,H,W,-1)
        value=torch.addcmul(value,ca[2].to(residual_dtype),out.to(residual_dtype))
    n=norm(value,block.layer_norm_mlp,mlp[1],mlp[0]).to(compute_dtype)
    value=torch.addcmul(value,mlp[2].to(residual_dtype),block.mlp(n).to(residual_dtype))
    return value,own


def weight_signature(dm, patcher=None):
    """Track Comfy native hook selection as well as mutable parameter storage."""
    params=[]
    for name,p in dm.named_parameters():
        try:
            version=p._version
        except RuntimeError:
            version=None  # Comfy can load parameters inside inference_mode.
        params.append((name,p.data_ptr(),version))
    hooks=getattr(patcher,'current_hooks',None)
    hook_state=tuple((id(h),h.strength) for h in hooks.hooks) if hooks is not None else ()
    return tuple(params),hook_state


class AsymmetricRuntime(FrameRuntime):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if self.slots and self.plan.character_mode!='precision':
            raise ValueError('Experimental v2 uses precision numbered reference predictions.')
        self.ref_banks={}
        self.audit.update(backend='asymmetric_v2',reference_prefills=0,reference_cache_hits=0,
                          reference_prefill_seconds=0.,peak_reference_cache_bytes=0)

    def clear(self):
        self.ref_banks.clear()
        # The patcher owns this runtime through model_options/wrappers. Break
        # the back-reference after sampling so Comfy can unload it normally.
        self.model_patcher = None
        super().clear()

    def load_weights(self,dm):
        if len(dm.blocks)!=28:
            raise ValueError('Anima reference v2 weights require the 28-block Anima 2B model. / v2는 현재 Anima 2B용입니다.')
        super().load_weights(dm)

    def mark(self,executor,x,timesteps,context,*args,**kwargs):
        def next_(x,timesteps,context,*args,**kwargs):
            opts=dict(kwargs.get('transformer_options',{}))
            opts['rs_reference_frame']=False  # target queries only
            opts['rs_reference_asymmetric']=kwargs.get('rs_anima_ref_frame') is not None
            opts.pop('rs_reference_slots',None)
            opts.pop('rs_reference_count',None)
            kwargs['transformer_options']=opts
            return executor(x,timesteps,context,*args,**kwargs)
        return super().mark(next_,x,timesteps,context,*args,**kwargs)

    def ref_forward(self,dm,x,timesteps,context,reference,options):
        if options.get('patches') or options.get('patches_replace') or options.get('optimized_attention_override'):
            raise ValueError('Experimental Anima v2 does not yet support other model attention patches.')
        import comfy.ldm.common_dit
        orig=x.shape
        x=comfy.ldm.common_dit.pad_to_patch_size(x,(dm.patch_temporal,dm.patch_spatial,dm.patch_spatial))
        ref=comfy.ldm.common_dit.pad_to_patch_size(reference[:1].to(x),(dm.patch_temporal,dm.patch_spatial,dm.patch_spatial))
        if ref.shape[2]!=1:
            raise ValueError('Use precision numbered banks with Anima v2, one source per prediction.')
        target_grid=tuple(s//dm.patch_spatial for s in x.shape[-2:])
        # Exact content identity, scoped to this run; never a sum-based fingerprint.
        content=hashlib.sha256(ref.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes()).digest()
        # Native precise LoRA hooks may swap or update base parameters between
        # predictions. Never reuse a reference bank across different weights.
        signature=weight_signature(dm,getattr(self,'model_patcher',None))
        if getattr(self,'_weight_signature',signature)!=signature:
            self.ref_banks.clear()
        self._weight_signature=signature
        key=(id(dm),target_grid,tuple(ref.shape),x.device,x.dtype,content)
        if getattr(self,'_cache_grid',target_grid)!=target_grid:
            self.ref_banks.clear()  # no stale progressive-stage residency
        self._cache_grid=target_grid
        bank=self.ref_banks.get(key)
        if bank is None:
            torch.cuda.synchronize(x.device) if x.is_cuda else None
            start=time.monotonic()
            value,rope,emb,adaln=frame_embed(dm,ref,torch.zeros(1,device=x.device),True,target_grid)
            bank=[]
            for block in dm.blocks:
                value,kv=asym_block(block,value,emb,adaln,rope)
                bank.append(kv)
            self.ref_banks[key]=bank
            torch.cuda.synchronize(x.device) if x.is_cuda else None
            self.audit['reference_prefills']+=1
            self.audit['reference_prefill_seconds']+=time.monotonic()-start
            total=sum(t.numel()*t.element_size() for b in self.ref_banks.values() for kv in b for t in kv)
            self.audit['peak_reference_cache_bytes']=max(self.audit['peak_reference_cache_bytes'],total)
        else:self.audit['reference_cache_hits']+=1
        value,rope,emb,adaln=frame_embed(dm,x,timesteps.reshape(x.shape[0],-1)[:,0])
        for i,block in enumerate(dm.blocks):
            options['block_index']=i
            value,_=asym_block(block,value,emb,adaln,rope,context,bank[i],options)
        out=dm.unpatchify(dm.final_layer(value.to(context.dtype),emb,adaln_lora_B_T_3D=adaln))
        return out[:,:,:orig[-3],:orig[-2],:orig[-1]]
