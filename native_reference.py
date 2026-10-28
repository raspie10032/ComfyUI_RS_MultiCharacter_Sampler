"""Private native reference-latent binding; model-specific routing consumes it."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
from .reference_image import prepare_reference,reference_size_input

def attach_native_references(routing,work):
    refs=work.model_options.get('rs_native_reference',[])
    routing.reference_plan=refs
    routing.reference_latents=[work.model.process_latent_in(r['latent']) for r in refs]
    routing.reference_lengths=[]
    routing.reference_audit=dict(backend='native reference latents',family=routing.family,
        refs=[{k:v for k,v in r.items() if k not in ('latent', 'pixels')} for r in refs],calls=0,blocks_seen=[],reference_lengths=[])
    if refs:
        routing.audit['image_reference']=routing.reference_audit

def reference_joint(routing, original,q,k,v,heads,mask=None,**kwargs):
    """Per-slot references never attend to other characters or the output image.

    Target queries receive own caption and own reference K/V only. Common text
    sees the target canvas, so it cannot shuttle reference features across slots.
    """
    from .routing import BoxGroups
    import math
    state=routing.state
    pre=kwargs.get('skip_reshape',False);dim=2 if pre else 1
    outpre=kwargs.get('skip_output_reshape',False);odim=2 if outpre else 1
    n=q.shape[dim];ni=state['image_tokens'];nt=sum(state['lengths']);nr=sum(routing.reference_lengths)
    if n!=ni+nt+nr:raise ValueError(f'{routing.family} reference sequence mismatch: {n} vs {ni}+{nt}+{nr}')
    if routing.family in ('FLUX3','MOSS'):
        istart=0;rstart=ni;tstart=ni+nr
    elif routing.family == 'Krea2':
        tstart=0;rstart=nt;istart=nt+nr
    else:tstart=0;istart=nt;rstart=nt+ni
    def ids(a,b):return torch.arange(a,b,device=q.device)
    text=[];start=tstart
    for length in state['lengths']:text.append(ids(start,start+length));start+=length
    refs=[];start=rstart
    for length in routing.reference_lengths:refs.append(ids(start,start+length));start+=length
    images=ids(istart,istart+ni)
    out=q.new_empty((1,heads,n,q.shape[-1]//heads)) if outpre and not pre else (q.new_empty((1,n,heads*q.shape[-1])) if pre and not outpre else torch.empty_like(q))
    def attend(qi,ki,bias=None,gain=None):
        if not len(qi):return
        values=v.index_select(dim,ki)
        if gain is not None:
            shape=[1]*values.ndim;shape[dim]=len(ki);values=values*gain.reshape(shape)
        result=original(q.index_select(dim,qi),k.index_select(dim,ki),values,heads,mask=bias,**kwargs)
        out.index_copy_(odim,qi,result)
    attend(text[0],torch.cat((text[0],images)))
    for i,t in enumerate(text[1:]):
        own_refs=[refs[j] for j,r in enumerate(routing.reference_plan) if r['slot']==i]
        attend(t,torch.cat((t,state['groups'][i]+istart,*own_refs)))
    for j,ref in enumerate(refs):
        slot=routing.reference_plan[j]['slot']
        attend(ref,torch.cat((ref,text[0],text[slot+1],state['groups'][slot]+istart)))
    groups=state['groups']
    cells=groups.cells if isinstance(groups,BoxGroups) else [((i,),g) for i,g in enumerate(groups)]
    for members,queries in cells:
        if not members:attend(queries+istart,torch.cat((text[0],images)));continue
        captions=[text[i+1] for i in members]
        matching=[j for j,r in enumerate(routing.reference_plan) if r['slot'] in members]
        refkeys=[refs[j] for j in matching]
        keys=torch.cat((text[0],*captions,images,*refkeys))
        nc=len(text[0]);ntc=sum(len(t) for t in captions);mass=nc/(1+state['common'])
        # Each ownership cell shares the same key priors. Broadcast one row
        # rather than materializing a quadratic query-by-key table.
        bias=q.new_zeros((len(queries) if routing.family == 'MOSS' else 1,len(keys)))
        bias[:,:nc]=-torch.inf if not state['common'] else math.log(state['common']*mass/nc)
        start=nc
        for t in captions:bias[:,start:start+len(t)]=math.log(mass/(len(members)*len(t)));start+=len(t)
        if state['separation']:
            bias[:,start:start+ni]=-torch.inf if state['separation'] == 1 else math.log1p(-state['separation'])
            for i in members:bias[:,start+groups[i]]=0
            if isinstance(groups,BoxGroups):bias[:,start+groups.background]=0
        gain=q.new_ones(len(keys));gain[nc:nc+ntc]=state['gain']
        start+=ni
        for j in matching:
            bias[:,start:start+len(refs[j])]=math.log(routing.reference_plan[j]['strength'])
            start+=len(refs[j])
        attend(queries+istart,keys,bias,gain)
    routing.reference_audit['calls']+=1
    state['record']['joint_calls']+=1;routing.audit['cross_calls']+=1;routing.audit['self_calls']+=1
    return out
def moss_reference_forward(dm,x,timestep,context,refs,options):
    """Unused RoPE r-axis reference input, with per-slot regional attention."""
    from comfy.ldm.flux.layers import timestep_embedding
    from comfy.ldm.moss_image.model import modulated_rms_norm
    import comfy.model_prefetch
    b,_,h,w=x.shape;dtype=x.dtype;device=x.device
    nt=context.shape[1];ni=h*w
    def coords(hh,ww,index):
        ids=torch.zeros(hh*ww,4,device=device)
        ids[:,0]=index;ids[:,1]=nt
        ids[:,2]=(torch.arange(hh,device=device)-(hh-1)/2).repeat_interleave(ww)
        ids[:,3]=(torch.arange(ww,device=device)-(ww-1)/2).repeat(hh)
        return ids
    imgids=[coords(h,w,0)]+[coords(r.shape[-2],r.shape[-1],i+1) for i,r in enumerate(refs)]
    for refids,(cx,cy) in zip(imgids[1:],options.get('rs_mc_ref_centers',[])):
        refids[:,2]+=cy-(h-1)/2
        refids[:,3]+=cx-(w-1)/2
    textids=torch.zeros(nt,4,device=device);textids[:,1]=torch.arange(nt,device=device)
    pe=dm.pe_embedder(torch.cat((*imgids,textids))[None]).transpose(1,2).contiguous()
    nr=sum(r.shape[-2]*r.shape[-1] for r in refs)
    vec=dm.time_embedding(timestep_embedding(timestep,256).to(dtype))
    mod=dm.shared_block_modulation(vec).unflatten(-1,(6,-1)).unsqueeze(2).unbind(1)
    shift,scale=dm.video_head_modulation(vec).unflatten(-1,(2,-1)).unsqueeze(2).unbind(1)
    txt=dm.text_embedder(context,pe[:,ni+nr:],options)
    tokens=[dm.video_embedder(z.flatten(2).transpose(1,2)) for z in [x]+refs]
    hidden=torch.cat((*tokens,txt),1)
    options={**options,'total_blocks':len(dm.layers),'block_type':'single'}
    queue=comfy.model_prefetch.make_prefetch_queue(list(dm.layers),device,options)
    comfy.model_prefetch.malloc_graph_begin(device)
    for i,block in enumerate(dm.layers):
        comfy.model_prefetch.prefetch_queue_pop(queue,device,block,dtype,malloc_scope='block')
        options['block_index']=i;hidden=block(hidden,mod,pe,options)
    comfy.model_prefetch.prefetch_queue_pop(queue,device,None,dtype,malloc_scope='block')
    comfy.model_prefetch.malloc_graph_end()
    out=dm.final_linear_video(modulated_rms_norm(hidden[:,:ni],dm.final_norm_video,scale,shift))
    return out.transpose(1,2).reshape(b,dm.latent_channels,h,w)
