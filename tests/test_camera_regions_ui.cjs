// SPDX-License-Identifier: GPL-3.0-only
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict'),cp=require('node:child_process');
const strip=s=>s.replace(/^import[^\n]*\n/gm,'').replaceAll('export function','function');
const camera={app:{registerExtension(){}}};
vm.runInNewContext(strip(fs.readFileSync('web/camera_control.js','utf8')),camera);
const region={projectLayout:camera.projectLayout,randomCamera:camera.randomCamera};
vm.runInNewContext(strip(fs.readFileSync('web/camera_regions.js','utf8')),region);
const plain=x=>JSON.parse(JSON.stringify(x));
const node=(settings={},links=[])=>({widgets:Object.entries(settings).map(([name,value])=>({name,value})),inputs:links.map(name=>({name,link:1}))});
const width=32,height=48,data=new Uint8Array(width*height);
for(let y=8;y<39;y++)for(let x=6;x<18;x++)data[y*width+x]=1;
const support={width,height,data,center:[12/32,23.5/48]};
const slots=[{id:1,kind:'character',masked:true,maskSupport:support},
    {id:2,kind:'character',geometry:'box',x:.65,y:.5,width:.3,height:.4},
    {id:3,kind:'character',geometry:'point',x:.6,y:.55},
    {id:4,kind:'text',geometry:'box',x:.5,y:.1,width:.8,height:.1}];
const original=plain(slots);
const probes=['distance_and_roll','perspective'].flatMap(layout_sync=>[1,1.5,2/3].flatMap(canvas_aspect=>[-20,0,25].map(roll=>({layout_sync,canvas_aspect,roll,distance:.65,azimuth:35,elevation:20}))));
const python=cp.spawnSync(process.env.CAMERA_PYTHON||'python',['-c',`
import json,sys,base64,numpy as np
from dataclasses import dataclass
from camera_layout import _warp,framing,perspective_framing,project
@dataclass(frozen=True)
class Mask:
    width:int
    height:int
    packed:bytes
p=json.load(sys.stdin)
mask=Mask(p['width'],p['height'],np.packbits(p['data']).tobytes())
out=[]
for v in p['probes']:
    args=(v['distance'],v['roll'],v['canvas_aspect'])
    t=perspective_framing(*args,v['azimuth'],v['elevation']) if v['layout_sync']=='perspective' else framing(*args)
    m=_warp(mask,t)
    ps=[project(x,y,t) for x in (.5,.8) for y in (.3,.7)]
    l,r=max(0,min(x for x,y in ps)),min(1,max(x for x,y in ps))
    top,b=max(0,min(y for x,y in ps)),min(1,max(y for x,y in ps))
    out.append(dict(mask=np.unpackbits(np.frombuffer(m.packed,dtype=np.uint8),count=m.width*m.height).tolist(),box=[(l+r)/2,(top+b)/2,r-l,b-top],point=project(.6,.55,t)))
print(json.dumps(out))
`],{input:JSON.stringify({width,height,data:Array.from(data),probes}),encoding:'utf8'});
assert.equal(python.status,0,python.stderr);
JSON.parse(python.stdout).forEach((expected,index)=>{
    const n=node(probes[index]),actual=region.cameraSlots(n,slots);
    assert.equal(actual.unknown,false);
    assert.deepEqual(Array.from(actual.slots[0].maskSupport.data),expected.mask);
    for(const [i,key]of ['x','y','width','height'].entries())assert.ok(Math.abs(actual.slots[1][key]-expected.box[i])<1e-12);
    for(const [i,key]of ['x','y'].entries())assert.ok(Math.abs(actual.slots[2][key]-expected.point[i])<1e-12);
    assert.equal(actual.slots[3],slots[3]);
    assert.equal(region.cameraSlots(n,slots).slots[0].maskSupport,actual.slots[0].maskSupport);
});
assert.deepEqual(plain(slots),original);
for(const settings of [{},{enabled:false,layout_sync:'perspective'},{strength:0,layout_sync:'distance_and_roll'}])assert.equal(region.cameraSlots(node(settings),slots).slots,slots);
const bypass=node({layout_sync:'perspective',azimuth:90});bypass.mode=4;
assert.equal(region.cameraSlots(bypass,slots).unknown,false);
assert.equal(region.cameraSlots(node({layout_sync:'perspective',azimuth:90}),slots).unknown,true);
assert.equal(region.cameraSlots(node({layout_sync:'distance_and_roll'},['distance']),slots).unknown,true);
assert.equal(region.cameraSlots(node({layout_sync:'fixed'},['distance']),slots).unknown,false);
assert.equal(region.cameraSlots(node({layout_sync:'distance_and_roll'},['azimuth']),slots).unknown,false);
assert.equal(region.cameraSlots(node({layout_sync:'perspective'},['azimuth']),slots).unknown,true);
assert.equal(region.cameraSlots(node({layout_sync:'distance_and_roll',random_mode:'balanced',random_seed:123}),slots).unknown,false);
assert.equal(region.cameraSlots(node({layout_sync:'distance_and_roll',random_mode:'balanced'},['random_seed']),slots).unknown,true);
assert.equal(region.cameraSlots(node({},['enabled']),[]).unknown,false);
assert.equal(region.cameraSlots(node({layout_sync:'distance_and_roll'}),[{id:1,masked:true}]).unknown,true);
assert.equal(region.cameraSlots(node({layout_sync:'distance_and_roll',random_mode:'invalid'}),slots).unknown,true);
assert.equal(region.cameraSlots(node({layout_sync:'distance_and_roll',random_mode:'balanced',random_seed:-1}),slots).unknown,true);
const muted=node();muted.mode=2;assert.equal(region.cameraSlots(muted,slots).unknown,true);
assert.equal(region.cameraSlots(node(),[{id:1,dynamic:true}]).unknown,true);
console.log('Camera region previews: 18 Python raster/box/point parity cases, fixed text, cached masks, random/linked/off/bypass safeguards passed');
