"""Experimental SD-family learned IP-Adapter residual integrated into RS routing.

ImageProj/K/V math follows h94/IP-Adapter (Apache-2.0), no runtime import of
another custom node. Uses pooled ViT-H features at its native 224 input.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
from safetensors.torch import load_file
from .reference_image import prepare_reference, reference_size_input

class SDReferenceRuntime:
    def __init__(self,plan,audit):
        family,self.refs,*profile=plan
        from .reference_assets import asset
        self.audit=audit['image_reference']=dict(family=family,backend='h94 learned IP-Adapter Plus',
            refs=[{k:v for k,v in r.items() if k!='features'} for r in self.refs],calls=0,
            blocks_seen=[],outside_region_residual_max=0.,tokens_per_ref=16,encoder_native_size=224)
        weights=load_file(str(asset('sdxl_adapter' if family=='SDXL' else 'sd15_adapter')))
        self.weights={k:v.float() for k,v in weights.items()}
        self.tokens=[];self.kv={}
        from .sd_resampler import Resampler
        w=self.weights
        dim=w['image_proj.latents'].shape[-1]
        projector=Resampler(dim=dim,depth=4,dim_head=64,heads=dim//64,num_queries=16,embedding_dim=1280,output_dim=w['image_proj.proj_out.weight'].shape[0],ff_mult=4)
        projector.load_state_dict({k.removeprefix('image_proj.'):v for k,v in w.items() if k.startswith('image_proj.')})
        projector.eval()
        with torch.inference_mode():
            for r in self.refs:
                self.tokens.append(tuple(projector(f.float()) for f in r['features']))

    def apply(self,routing,q,k,v,options,base):
        if not self.refs:return base
        block=options['block'];index=options.get('block_index',0)
        # BasicTransformerBlock supplies transformer_index within SpatialTransformer.
        tr=options.get('block_index',0)
        key=tuple(block)+(tr,) if routing.family=='SDXL' else tuple(block)
        module=routing.reference_modules[key]
        heads=options['n_heads']; d=q.shape[-1]//heads
        (_,_,_),groups=routing._inputs(q,k,v,options)
        result=base.clone()
        for i,r in enumerate(self.refs):
            queries=groups[r['slot']]
            if not len(queries):continue
            cache=(i,module,q.device,q.dtype)
            if cache not in self.kv:
                kv=[]
                for tokens in self.tokens[i]:
                    kv.append(tuple(F.linear(tokens.to(q),self.weights[f'ip_adapter.{module}.to_{kind}_ip.weight'].to(q)) for kind in ('k','v')))
                self.kv[cache]=kv
            positive,negative=self.kv[cache]
            ki=torch.cat([(negative if kind else positive)[0] for kind in routing.state['kinds']],0)
            vi=torch.cat([(negative if kind else positive)[1] for kind in routing.state['kinds']],0)
            qt=q.index_select(1,queries).reshape(q.shape[0],-1,heads,d).transpose(1,2)
            kt=ki.reshape(ki.shape[0],-1,heads,d).transpose(1,2)
            vt=vi.reshape(vi.shape[0],-1,heads,d).transpose(1,2)
            extra=F.scaled_dot_product_attention(qt,kt,vt).transpose(1,2).flatten(2)*r['strength']
            result.index_add_(1,queries,extra.to(result))
        self.audit['calls']+=1
        if list(key) not in self.audit['blocks_seen']:self.audit['blocks_seen'].append(list(key))
        return result
