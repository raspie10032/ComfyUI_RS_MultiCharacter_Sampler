# SPDX-License-Identifier: GPL-3.0-only
"""Research extension of AnticPan NativeEngine using RS per-region routing.

Upstream: https://huggingface.co/AnticPan/Anima-Role-Ref-KV
The Apache-licensed native engine is in anima_role_native.py; license accompanies it.
Reference caches are invocation-local, per character; no process-global reuse.
"""
import math
import torch
import torch.nn.functional as F
from .anima_role_native import NativeEngine
from .routing import route_cross, token_groups, sdpa


def regional_cached_attention(q,k,v,groups,target_bias,cache_banks,strengths):
    """Generated tokens can read only their own reference banks before softmax.

    q/k/v use [B,token,head,dim]. Cache banks use upstream [B,head,token,dim].
    Non-overlap reads one bank; overlap reads all owners; background none.
    Variable reference lengths are supported without generating reference Q.
    """
    if len(cache_banks)!=len(groups) or len(strengths)!=len(groups):
        raise ValueError('Exactly one cache entry and strength per region required')
    out=q.new_empty(q.shape[:2]+(q.shape[2]*q.shape[3],))
    cells=getattr(groups,'cells',None)
    if cells is None:cells=[((i,),ids) for i,ids in enumerate(groups)]
    for owners,ids in cells:
        if not len(ids):continue
        keys=[k];values=[v]
        # The balanced profile needs a key prior, not a Q-by-K dense mask.
        # Broadcast a single row across all query tokens in this region.
        bias_rows = 1 if target_bias is None else len(ids)
        bias=[q.new_zeros((bias_rows,k.shape[1])) if target_bias is None else target_bias[ids]]
        for slot in owners:
            pair=cache_banks[slot]
            strength=strengths[slot]
            if pair is None or strength==0:continue
            if not math.isfinite(strength) or strength<0:raise ValueError('Invalid reference strength')
            rk,rv=pair
            if rk.shape!=rv.shape or rk.shape[:2]!=(q.shape[0],q.shape[2]) or rk.shape[-1]!=q.shape[-1]:
                raise ValueError('Reference cache shape mismatch')
            keys.append(rk.transpose(1,2));values.append(rv.transpose(1,2))
            bias.append(q.new_full((bias_rows,rk.shape[2]),math.log(strength)))
        out[:,ids]=sdpa(q[:,ids],torch.cat(keys,1),torch.cat(values,1),torch.cat(bias,1))
    return out


class RegionalRoleEngine(NativeEngine):
    def __init__(self,*args,masks,common_tokens,reference_strengths,boxes=True,profile="rs",**kwargs):
        super().__init__(*args,**kwargs)
        self.device=next(self.net.parameters()).device
        self.masks=masks;self.common_tokens=common_tokens
        self.boxes=boxes
        self.reference_strengths=reference_strengths
        self.profile=profile
        self.preparing=False;self.positive=True
        self.groups=None;self.grid=None;self.step=0;self.total_steps=30
        self.lengths=None;self.target_bias=None
        self.records=[];self.pair=None

    def reference(self,*args,**kwargs):
        self.preparing=True
        try:return super().reference(*args,**kwargs)
        finally:self.preparing=False

    def configure(self,step,total_steps,grid,lengths,positive):
        self.step=step;self.total_steps=total_steps;self.lengths=lengths;self.positive=positive
        if self.grid!=tuple(grid):
            self.grid=tuple(grid)
            self.groups=token_groups(self.masks,*grid,self.device,boxes=self.boxes)
        self.prior=1.
        self.gain=1.
        # The trained adapter collapsed under the original strong isolation.
        # Generated image tokens remain mutually visible; only reference banks
        # are restricted by region ownership. Avoid a dense NxN zero matrix.
        self.target_bias=None

    def block(self,block,h,ctx,e,t,rope,i,ref=None,cache_only=False):
        if self.preparing:
            return super().block(block,h,ctx,e,t,rope,i,ref,cache_only)
        # Preserve upstream normalization eps, learned time modulation, adapter
        # algebra and activation. Only the two attention operations change.
        n,gate=self.norm(block,h,e,t,"self_attn")
        q,k,v=self.qkv(block.self_attn,n,i,rope)
        own=(k,v)
        banks=ref if ref is not None else [None]*len(self.groups)
        o=regional_cached_attention(q.transpose(1,2),k.transpose(1,2),v.transpose(1,2),
            self.groups,self.target_bias,banks,self.reference_strengths)
        h=h+gate*self.linear(block.self_attn.output_proj,o,i,"self_attn.output_proj")
        n,gate=self.norm(block,h,e,t,"cross_attn")
        a=block.cross_attn
        q=self.rms(a.q_norm,a.q_proj(n).unflatten(-1,(a.n_heads,-1)).transpose(1,2),1e-5)
        k=self.rms(a.k_norm,a.k_proj(ctx).unflatten(-1,(a.n_heads,-1)).transpose(1,2),1e-5)
        v=a.v_proj(ctx).unflatten(-1,(a.n_heads,-1)).transpose(1,2)
        if self.profile!="minimal":
            o=route_cross(q.transpose(1,2),k.transpose(1,2),v.transpose(1,2),self.groups,
                self.lengths,[0 if self.positive else 1],weights=None if self.profile=="text" else (self.prior,1.),
                common_tokens=None if self.profile=="text" else self.common_tokens,character_gain=self.gain)
        else:o=F.scaled_dot_product_attention(q,k,v).transpose(1,2).flatten(2)
        h=h+gate*a.output_proj(o)
        n,gate=self.norm(block,h,e,t,"mlp")
        o=block.mlp.activation(self.linear(block.mlp.layer1,n,i,"mlp.layer1"))
        return h+gate*self.linear(block.mlp.layer2,o,i,"mlp.layer2"),own
