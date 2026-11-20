// SPDX-License-Identifier: GPL-3.0-only
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict'),cp=require('child_process');
const source=fs.readFileSync('web/camera_control.js','utf8').replace(/^import[^\n]*\n/gm,'').replaceAll('export function','function')
 .replaceAll('import.meta.url', "'http://localhost/extensions/sampler/camera_control.js'");
let locale='en';
const extensions={};
const app={extensionManager:{setting:{get:()=>locale}},registerExtension:e=>extensions[e.name]=e};
const drawnText=[];
const context2d=new Proxy({fillText(s){drawnText.push(s);}}, {get:(obj,name)=>obj[name] ?? (()=>{}),set:(obj,name,value)=>(obj[name]=value,true)});
const element=()=>({style:{},children:[],listeners:{},attributes:{},append(...items){this.children.push(...items);},setAttribute(name,value){this.attributes[name]=value;},addEventListener(name,fn){this.listeners[name]=fn;},getContext(){return context2d;},setPointerCapture(id){this.captured=id;},hasPointerCapture(id){return this.captured===id;},releasePointerCapture(){this.captured=undefined;},focus(){},getBoundingClientRect(){return {left:10,top:20,width:320,height:175};}});
const trainedRows=JSON.parse(fs.readFileSync('web/atelier_camera_views.json','utf8'));
const sandbox={app,document:{createElement:element},console,URL,atob:s=>Buffer.from(s,'base64').toString('binary'),
 fetch:async url=>{
  assert.equal(url.pathname,'/extensions/sampler/atelier_camera_views.json');
  return {ok:true,json:async()=>trainedRows};
 }};
vm.runInNewContext(source,sandbox);
// With NAI loaded first, keep its own node untouched but move the common
// compatibility ID out of the default menu even if NAI owns its definition.
const sharedGuardSandbox = {...sandbox, app:{...app, registerExtension(e) { this.extensions[e.name] = e; }, extensions:{}}};
vm.runInNewContext('globalThis[Symbol.for("raspie.camera.editor")] = true;', sharedGuardSandbox);
vm.runInNewContext(source, sharedGuardSandbox);
const foreignDefs = {RSCameraControl:{category:'NAI/Camera'}, NAICameraControl:{category:'NAI/Camera'}};
sharedGuardSandbox.app.extensions['RS.LegacyCameraDefinition'].addCustomNodeDefs(foreignDefs);
assert.equal(foreignDefs.RSCameraControl.category, 'RS MultiCharacter/Legacy');
assert.equal(foreignDefs.RSCameraControl.deprecated, true);
assert.deepEqual(foreignDefs.NAICameraControl, {category:'NAI/Camera'});
assert.equal(sharedGuardSandbox.app.extensions['RS.CameraControl'], undefined);
assert.ok(sharedGuardSandbox.app.extensions['RS.AtelierSphereCameraControl']);
assert.ok(sharedGuardSandbox.app.extensions['RS.UnifiedCameraControl']);
const coordinates=[];
for(let i=0;i<301;i++) coordinates.push({azimuth:-180+360*i/300,elevation:-90+180*(i%37)/36,distance:(i%61)/60,roll:-45+90*(i%17)/16,strength:5*(i%13)/12});
const python=cp.spawnSync(process.env.CAMERA_PYTHON||'python',['-c','import json,sys;from camera_control import camera_weights;print(json.dumps([camera_weights(**v) for v in json.load(sys.stdin)]))'],{input:JSON.stringify(coordinates),encoding:'utf8'});
assert.equal(python.status,0,python.stderr);
const expected=JSON.parse(python.stdout);
const captionProbes=coordinates.flatMap(v=>['ComfyUI','NovelAI'].flatMap(syntax=>['weighted','plain'].map(weighting=>({weights:sandbox.cameraWeights(v),syntax,weighting}))));
const captionsPython=cp.spawnSync(process.env.CAMERA_PYTHON||'python',['-c','import json,sys;from camera_control import camera_caption;print(json.dumps([camera_caption(**v) for v in json.load(sys.stdin)]))'],{input:JSON.stringify(captionProbes),encoding:'utf8'});
assert.equal(captionsPython.status,0,captionsPython.stderr);
assert.deepEqual(captionProbes.map(p=>sandbox.cameraCaption(p.weights,p.syntax,p.weighting)),JSON.parse(captionsPython.stdout));

const seeds=[0,1,12345,0x7fffffff,0xffffffff];
const randomProbes=['balanced','full'].flatMap(mode=>seeds.map(seed=>({mode,seed})));
const randomPython=cp.spawnSync(process.env.CAMERA_PYTHON||'python',['-c','import json,sys;from camera_control import random_camera;print(json.dumps([random_camera(**v) for v in json.load(sys.stdin)]))'],{input:JSON.stringify(randomProbes),encoding:'utf8'});
assert.equal(randomPython.status,0,randomPython.stderr);
assert.deepEqual(JSON.parse(JSON.stringify(randomProbes.map(v=>sandbox.randomCamera(v.mode,v.seed)))),JSON.parse(randomPython.stdout));
const layoutProbes=coordinates.map((v,i)=>[.2,.7,v.distance,v.roll,[1,1.5,2/3][i%3]]);
const layoutPython=cp.spawnSync(process.env.CAMERA_PYTHON||'python',['-c','import json,sys;from camera_layout import project,framing;print(json.dumps([project(x,y,framing(d,r,a)) for x,y,d,r,a in json.load(sys.stdin)]))'],{input:JSON.stringify(layoutProbes),encoding:'utf8'});
assert.equal(layoutPython.status,0,layoutPython.stderr);
JSON.parse(layoutPython.stdout).forEach((p,i)=>p.forEach((v,j)=>assert.ok(Math.abs(v-sandbox.projectLayout(...layoutProbes[i])[j])<1e-12)));

const perspectiveProbes=coordinates.filter(v=>Math.abs(Math.cos(v.azimuth*Math.PI/180)*Math.cos(v.elevation*Math.PI/180))>1e-6).flatMap((v,i)=>[[.2,.3],[.8,.7]].map(([x,y])=>[x,y,v.distance,v.roll,[1,1.5,2/3][i%3],v.azimuth,v.elevation]));
const perspectivePython=cp.spawnSync(process.env.CAMERA_PYTHON||'python',['-c','import json,sys;from camera_layout import project,perspective_framing;print(json.dumps([project(x,y,perspective_framing(d,r,a,yaw,pitch)) for x,y,d,r,a,yaw,pitch in json.load(sys.stdin)]))'],{input:JSON.stringify(perspectiveProbes),encoding:'utf8'});
assert.equal(perspectivePython.status,0,perspectivePython.stderr);
JSON.parse(perspectivePython.stdout).forEach((p,i)=>p.forEach((v,j)=>assert.ok(Math.abs(v-sandbox.projectLayout(...perspectiveProbes[i],true)[j])<1e-12)));
for(let i=0;i<coordinates.length;i++){
  const actual=sandbox.cameraWeights(coordinates[i]);
  for(const tag of new Set([...Object.keys(expected[i]),...Object.keys(actual)])) assert.ok(Math.abs((actual[tag]||0)-(expected[i][tag]||0))<1e-10,`${i}: ${tag}`);
}
// Camera markers and captions must agree at front/back/left/right and stay independent of height.
for (const [azimuth,sector,dx,dy] of [[0,0,0,1],[90,2,1,0],[180,4,0,-1],[-180,4,0,-1],[-90,6,-1,0]]) {
  const d=sandbox.cameraDiagram({azimuth});
  assert.equal(d.sector,sector);
  assert.ok(Math.abs(d.top[0]-(164+82.5*dx))<1e-9);
  assert.ok(Math.abs(d.top[1]-(164+82.5*dy))<1e-9);
  assert.deepEqual(d.top,sandbox.cameraDiagram({azimuth,elevation:90}).top);
}
assert.ok(sandbox.cameraDiagram({elevation:90}).side[1]<164);
assert.ok(sandbox.cameraDiagram({elevation:-90}).side[1]>164);
assert.equal(sandbox.cameraDiagram({elevation:0}).side[1],164);
assert.ok(sandbox.cameraDiagram({distance:1}).top[1]>sandbox.cameraDiagram({distance:0}).top[1]);
for(const [angle,sector] of [[45,1],[135,3],[-135,5],[-45,7]]) assert.equal(sandbox.cameraDiagram({azimuth:angle}).sector,sector);

// The pointer angle is the inverse of the drawn camera position on both controls.
for(let azimuth=-180;azimuth<=180;azimuth+=15){
 const d=sandbox.cameraDiagram({azimuth,elevation:0,distance:.3});
 const angle=sandbox.cameraPointerAngle('azimuth',...d.top).azimuth;
 assert.ok(Math.abs((angle-azimuth+540)%360-180)<1e-9);
}
for(let elevation=-90;elevation<=90;elevation+=15){
 const d=sandbox.cameraDiagram({elevation,distance:.7});
 assert.ok(Math.abs(sandbox.cameraPointerAngle('elevation',...d.side).elevation-elevation)<1e-9);
}

class Node{
 constructor(){this.inputs=[];this.size=[340,200];this.widgets=Object.entries({azimuth:0,elevation:0,distance:.5,roll:0,strength:1.2,enabled:true,weighting:'weighted',prompt_syntax:'ComfyUI',random_mode:'off',random_seed:0,layout_sync:'fixed',canvas_aspect:1}).map(([name,value])=>({name,value,callback(){return 42;}}));}
 addDOMWidget(name,type,element,options){const w={name,type,element,options};this.widgets.push(w);return w;}
 setSize(size){this.size=size;}
 computeSize(){return [380,700];}
 setDirtyCanvas(){}
 onConfigure(){return 'configured';}
 onExecuted(){return 'executed';}
}
(async()=>{
 const extension=extensions['RS.CameraControl'];
 class AtelierNode extends Node {
  constructor(){super();this.widgets.push({name:'visible_details',value:true});}
 }
 await extensions['RS.AtelierSphereCameraControl'].beforeRegisterNodeDef(AtelierNode,{name:'RSAtelierSphereCameraControl'});
 const atelier=new AtelierNode();atelier.onNodeCreated();
 const [atelierModes,atelierToolbar,,,atelierCaption]=atelier.rsCameraEditor.root.children;
 const trainedViews=await sandbox.loadAtelierViews();
 const viewPoints=trainedRows.map(([azimuth,elevation])=>({azimuth:azimuth??0,elevation}));
 const viewProbes=[...viewPoints,...coordinates.map((v,i)=>({azimuth:v.azimuth+(i%7)*.017,elevation:v.elevation}))];
 const trainedPython=cp.spawnSync(process.env.CAMERA_PYTHON||'python',['-c',`
import json, sys, types
from pathlib import Path
root = types.ModuleType("rs_camera")
root.__path__ = [str(Path.cwd())]
sys.modules[root.__name__] = root
from rs_camera.atelier_camera import nearest_view
print(json.dumps([nearest_view(**v)[1] for v in json.load(sys.stdin)]))
`],{input:JSON.stringify(viewProbes),encoding:'utf8'});
 assert.equal(trainedPython.status,0,trainedPython.stderr);
 assert.deepEqual(viewProbes.map(v=>sandbox.nearestAtelierView(trainedViews,v).tags),JSON.parse(trainedPython.stdout));
 atelierToolbar.children.find(w=>w.textContent==='Face left').onclick();
 assert.equal(atelier.widgets.find(w=>w.name==='azimuth').value,-90);
 atelierToolbar.children.find(w=>w.textContent==='Face right').onclick();
 assert.equal(atelier.widgets.find(w=>w.name==='azimuth').value,90);
 assert.match(atelierCaption.textContent,/LoRA trained view · 90.0° \/ 0.0°/);
 const preview=atelierCaption.textContent;
 atelierModes.children[1].onclick();
 assert.equal(atelierCaption.textContent,preview);
 const trainedTag=sandbox.nearestAtelierView(trainedViews,{azimuth:90,elevation:0}).tags;
 atelier.onExecuted({camera_caption:[trainedTag+', backend tags'],camera_values:[{azimuth:90,elevation:0}]});
 atelierModes.children[0].onclick();
 assert.equal(atelierCaption.textContent,preview+', backend tags');
 atelier.widgets.find(w=>w.name==='visible_details').callback(false);
 assert.equal(atelierCaption.textContent,preview);

 class UnifiedNode extends Node {
  constructor(){
   super();
   this.widgets=[
    {name:'camera_mode',value:'merged_lora_only',type:'combo',computeSize:()=>[300,20],inputEl:{hidden:false},callback(){return 7;}},
    ...this.widgets.map(w=>({...w,type:'number',computeSize:()=>[300,20],inputEl:{hidden:false}})),
    {name:'control_after_generate',value:'fixed',type:'combo',computeSize:()=>[300,20],inputEl:{hidden:false}},
    {name:'lora_strength',value:1,type:'number',computeSize:()=>[300,20],inputEl:{hidden:false},callback(){return 8;}},
    {name:'visible_details',value:true,type:'toggle',computeSize:()=>[300,20],inputEl:{hidden:false}},
    {name:'anima_lora',value:'camera_v3',type:'combo',computeSize:()=>[300,20],inputEl:{hidden:false}},
   ];
  }
  computeSize(){return [380,40+this.widgets.reduce((n,w)=>n+(w.computeSize?.(380)[1]??20),0)];}
 }
 const unifiedDefs={name:'RSUnifiedCameraControl',input:{optional:{model:['MODEL'],building_pipe:['RS_MC_BUILD_PIPE'],context:['RS_MC_BUILD_PIPE']}}};
 await extensions['RS.UnifiedCameraControl'].beforeRegisterNodeDef(UnifiedNode,unifiedDefs);
 assert.ok(unifiedDefs.input.optional.model);
 assert.ok(unifiedDefs.input.optional.building_pipe);
 assert.equal(unifiedDefs.input.optional.context,undefined);
 const unified=new UnifiedNode();unified.onNodeCreated();
 const uWidget=name=>unified.widgets.find(w=>w.name===name);
 const uCustom=unified.widgets.at(-1);
 const [,uToolbar,,,uOutput]=unified.rsCameraEditor.root.children;
 assert.equal(uCustom.serialize,false);assert.equal(uCustom.options.serialize,false);
 // Default merged_lora_only is compact: hides camera angles/prompts/layout while allowing enabled and lora_strength.
 const compactHeight=unified.size[1];
 assert.ok(compactHeight < 235);
 assert.equal(uCustom.hidden,true);
 assert.ok(uCustom.computeSize()[1]<=0);
 for(const name of ['camera_mode','enabled','lora_strength']) assert.notEqual(uWidget(name).hidden,true);
 for(const name of ['azimuth','elevation','distance','roll','strength','weighting','prompt_syntax','random_mode','random_seed','control_after_generate','layout_sync','canvas_aspect','visible_details','anima_lora']){
  assert.equal(uWidget(name).hidden,true,`merged_lora_only should hide ${name}`);
  assert.equal(uWidget(name).inputEl.hidden,true);
 }
 assert.equal(unified.rsCameraEditor.root.style.display,'none');
 uWidget('lora_strength').value=.75;assert.equal(uWidget('lora_strength').callback(),8);
 // Switch to camera_and_lora: expands controls, shows trained view preview, and handles executed output.
 uWidget('strength').value=1.2;
 uWidget('camera_mode').value='camera_and_lora';assert.equal(uWidget('camera_mode').callback(),7);
 await Promise.resolve();await Promise.resolve();
 assert.equal(uCustom.computeSize()[1],670);
 assert.ok(unified.size[1]>compactHeight+400);
 for(const name of ['camera_mode','azimuth','elevation','enabled','lora_strength','visible_details','anima_lora','control_after_generate']){
  assert.notEqual(uWidget(name).hidden,true);
  assert.equal(uWidget(name).inputEl.hidden,false);
 }
 assert.notEqual(unified.rsCameraEditor.root.style.display,'none');
 uToolbar.children.find(w=>w.textContent==='Face right').onclick();
 assert.equal(uWidget('azimuth').value,90);
 assert.match(uOutput.textContent,/LoRA trained view · 90\.0° \/ 0\.0°/);
 unified.onExecuted({camera_caption:[trainedTag+', unified details'],camera_values:[{azimuth:90,elevation:0}]});
 assert.match(uOutput.textContent,/unified details/);
 // Switch to prompt_only: hides LoRA-only widgets and switches preview to prompt caption.
 uWidget('camera_mode').value='prompt_only';uWidget('camera_mode').callback();
 for(const name of ['lora_strength','visible_details','anima_lora']) assert.equal(uWidget(name).hidden,true);
 for(const name of ['camera_mode','azimuth','elevation','distance','roll','strength','prompt_syntax','enabled']) assert.notEqual(uWidget(name).hidden,true);
 assert.match(uOutput.textContent,/viewed from the right side/);
 sandbox.setCameraValues(unified,{prompt_syntax:'NovelAI',weighting:'plain'});
 assert.equal(uOutput.textContent,'viewed from the right side, medium shot');
 sandbox.setCameraValues(unified,{strength:0});assert.match(uOutput.textContent,/Camera OFF/);
 sandbox.setCameraValues(unified,{strength:1.2,weighting:'weighted'});
 // Switch back to merged_lora_only: returns to compact height and preserves all serialized values & order.
 const savedOrder=unified.widgets.filter(w=>w.serialize!==false).map(w=>w.name);
 const savedValues=unified.widgets.filter(w=>w.serialize!==false).map(w=>w.value);
 uWidget('camera_mode').value='merged_lora_only';uWidget('camera_mode').callback();
 assert.equal(unified.size[1],compactHeight);
 assert.deepEqual(unified.widgets.filter(w=>w.serialize!==false).map(w=>w.name),savedOrder);
 assert.deepEqual(unified.widgets.filter(w=>w.serialize!==false).map(w=>w.value).slice(1),savedValues.slice(1));
 // Save/reload simulation via onConfigure updates mode, visibility, and preview while preserving values.
 const reloaded=new UnifiedNode();reloaded.onNodeCreated();
 const reloadedWidgets=reloaded.widgets.filter(w=>w.serialize!==false);
 savedValues.forEach((val,i)=>{reloadedWidgets[i].value=val;});
 reloadedWidgets[0].value='camera_and_lora';
 reloaded.onConfigure();await Promise.resolve();await Promise.resolve();
 assert.equal(reloaded.widgets.find(w=>w.name==='azimuth').value,90);
 assert.equal(reloaded.widgets.find(w=>w.name==='lora_strength').value,.75);
 assert.equal(reloaded.widgets.find(w=>w.name==='prompt_syntax').value,'NovelAI');
 assert.notEqual(reloaded.widgets.find(w=>w.name==='azimuth').hidden,true);
 assert.match(reloaded.rsCameraEditor.root.children[4].textContent,/LoRA trained view · 90\.0° \/ 0\.0°/);
 reloadedWidgets[0].value='prompt_only';reloaded.onConfigure();
 assert.match(reloaded.rsCameraEditor.root.children[4].textContent,/::viewed from the right side::/);
 reloadedWidgets[0].value='merged_lora_only';reloaded.onConfigure();
 assert.equal(reloaded.widgets.find(w=>w.name==='azimuth').hidden,true);
 assert.equal(reloaded.widgets.find(w=>w.name==='azimuth').value,90);
 // Linked camera_mode expands controls and defers preview until execution.
 reloaded.inputs=[{name:'camera_mode',link:9}];reloaded.onConnectionsChange();
 assert.notEqual(reloaded.widgets.find(w=>w.name==='azimuth').hidden,true);
 assert.match(reloaded.rsCameraEditor.root.children[3].textContent,/camera_mode/);
 assert.match(reloaded.rsCameraEditor.root.children[4].textContent,/resolves on execution/);
 reloaded.onExecuted({camera_mode:['merged_lora_only']});
 assert.match(reloaded.rsCameraEditor.root.children[4].textContent,/Last run: merged LoRA only/);
 reloaded.onExecuted({camera_mode:['prompt_only'],camera_caption:['linked executed caption']});
 assert.equal(reloaded.rsCameraEditor.root.children[4].textContent,'linked executed caption');
 reloaded.inputs=[];reloaded.onConnectionsChange();
 assert.equal(reloaded.widgets.find(w=>w.name==='azimuth').hidden,true);
 // Converted widgets stay untouched across mode toggles.
 const converted=reloaded.widgets.find(w=>w.name==='azimuth');
 reloadedWidgets[0].value='camera_and_lora';reloaded.onConfigure();
 converted.type='converted-widget';converted.hidden=true;
 reloadedWidgets[0].value='merged_lora_only';reloaded.onConfigure();
 reloadedWidgets[0].value='camera_and_lora';reloaded.onConfigure();
 assert.equal(converted.type,'converted-widget');assert.equal(converted.hidden,true);

 await extension.beforeRegisterNodeDef(Node,{name:'RSCameraControl'});
 const defs={name:'RSCameraControl',input:{optional:{building_pipe:['RS_MC_CHARACTER_PIPE,NAI_CONTEXT'],context:['RS_MC_CHARACTER_PIPE,NAI_CONTEXT']}}};
 await extension.beforeRegisterNodeDef(class {},defs);
 assert.ok(defs.input.optional.building_pipe);assert.equal(defs.input.optional.context,undefined);
 const node=new Node();node.onNodeCreated();node.onNodeCreated();
 assert.equal(node.widgets.filter(w=>w.name==='rs_camera_editor').length,1);
 // Loading the old socket names keeps every connection and slot index.
 node.inputs=[{name:'base_prompt',link:7},{name:'context',link:12,label:'old context',localized_name:'공용 컨텍스트'}];
 node.outputs=[{name:'context',links:[18,19],type:'RS_MC_CHARACTER_PIPE'},{name:'prompt',links:[20]}];
 assert.equal(node.onConfigure(),'configured');
 assert.equal(node.inputs[1].name,'building_pipe');assert.equal(node.inputs[1].link,12);
 assert.equal(node.inputs[1].label,undefined);assert.equal(node.inputs[1].localized_name,undefined);
 assert.equal(node.outputs[0].name,'building_pipe');assert.deepEqual(node.outputs[0].links,[18,19]);
 assert.equal(node.outputs[1].name,'prompt');assert.equal(node.outputs[1].links[0],20);
 assert.equal(node.onConfigure(),'configured');assert.equal(node.inputs[1].name,'building_pipe');
 const editor=node.rsCameraEditor,custom=node.widgets.at(-1);
 assert.equal(custom.serialize,false);assert.equal(custom.options.serialize,false);
 const [modes,toolbar,canvas,notice,output,layoutNotice,layoutCanvas]=editor.root.children;
 const [dials,orbit]=modes.children;
 assert.equal(dials.attributes['aria-pressed'],'true');
 const value=name=>node.widgets.find(w=>w.name===name).value;
 const before=node.widgets.filter(w=>w.serialize!==false).map(w=>[w.name,w.value]);
 sandbox.setCameraValues(node,{prompt_syntax:'NovelAI'});assert.match(output.textContent,/::from front::/);
 sandbox.setCameraValues(node,{weighting:'plain'});assert.equal(output.textContent,'from front, medium shot');
 sandbox.setCameraValues(node,{strength:0});assert.match(output.textContent,/OFF/);
 sandbox.setCameraValues(node,{strength:1.2,weighting:'weighted',prompt_syntax:'ComfyUI'});
 node.inputs=[{name:'building_pipe',link:12}];editor.render();assert.match(notice.textContent,/Context syntax/);
 node.onExecuted({camera_caption:['NAI caption'],camera_syntax:['NovelAI']});
 sandbox.setCameraValues(node,{distance:.75});assert.match(output.textContent,/::full body::/);
 node.onConnectionsChange();assert.match(notice.textContent,/Context syntax/);
 node.inputs=[];sandbox.setCameraValues(node,{distance:.5});

 for(const lang of ['en','ko','ja','zh','zh-TW']){locale=lang;editor.render();assert.ok(notice.textContent.length>35);assert.ok(toolbar.children[0].textContent);}
 locale='en';
 drawnText.length=0;sandbox.setCameraValues(node,{azimuth:45,elevation:60});
 assert.ok(drawnText.some(s=>s.includes('Front-right · above')));
 assert.ok(drawnText.includes('TOP · direction'));assert.ok(drawnText.includes('SIDE · height'));
 toolbar.children[2].onclick();assert.equal(value('azimuth'),180);assert.equal(value('elevation'),0);
 assert.ok(drawnText.some(s=>s.includes('Behind · eye level')));
 locale='ko';drawnText.length=0;editor.render();assert.ok(drawnText.some(s=>s.includes('후면 · 눈높이')));
 locale='en';sandbox.setCameraValues(node,{azimuth:0,elevation:0});
 toolbar.children[1].onclick();assert.equal(value('azimuth'),90);
 // Pointer mapping uses the displayed (half-size, offset) canvas, never pixel deltas.
 const event=(x,y,id=1)=>({button:0,clientX:10+x/2,clientY:20+y/2,pointerId:id,preventDefault(){}});
 const click=(x,y)=>{canvas.onpointerdown(event(x,y));canvas.onpointerup(event(x,y));};
 sandbox.setCameraValues(node,{elevation:23});
 for(const [x,y,expected] of [[164,264,0],[264,164,90],[164,64,180],[64,164,-90],[214,114,135]]){
  click(x,y);assert.ok(Math.abs(value('azimuth')-expected)<1e-9);assert.equal(value('elevation'),23);
 }
 // A click in the centre or outside either control cannot reset an angle.
 click(164,164);assert.equal(value('azimuth'),135);click(10,10);assert.equal(value('azimuth'),135);
 for(const [x,y,expected] of [[556,164,0],[506,114,45],[456,64,90],[456,264,-90]]){
  click(x,y);assert.ok(Math.abs(value('elevation')-expected)<1e-9);assert.equal(value('azimuth'),135);
 }
 click(456,164);assert.equal(value('elevation'),-90);
 canvas.onpointerdown(event(264,164));
 canvas.onpointermove(event(556,64,2));assert.equal(value('azimuth'),90); // unrelated pointer
 canvas.onpointermove(event(556,64));assert.equal(value('elevation'),-90); // stays on initial axis
 canvas.onpointercancel(event(556,64));const cancelled=value('azimuth');
 canvas.onpointermove(event(64,164));assert.equal(value('azimuth'),cancelled);
 canvas.onpointerdown(event(556,164));canvas.onpointermove(event(400,64));assert.equal(value('elevation'),90);
 canvas.onlostpointercapture(event(400,64));canvas.onpointermove(event(456,264));assert.equal(value('elevation'),90);
 canvas.onpointerdown({...event(64,164),button:2});assert.equal(value('azimuth'),cancelled);
 // Preserve the linked axis and keep the other diagram usable.
 node.inputs=[{name:'azimuth',link:1}];click(64,164);assert.equal(value('azimuth'),cancelled);
 click(506,214);assert.equal(value('elevation'),-45);node.inputs=[];
 sandbox.setCameraValues(node,{azimuth:180,elevation:90});
 canvas.listeners.wheel({deltaY:1,shiftKey:false,preventDefault(){}});assert.equal(value('distance'),.525);
 canvas.listeners.wheel({deltaY:1,shiftKey:true,preventDefault(){}});assert.equal(value('roll'),2);
 canvas.onkeydown({key:'ArrowLeft',preventDefault(){}});assert.equal(value('azimuth'),175);
 node.inputs=[{name:'azimuth',link:1}];sandbox.setCameraValues(node,{azimuth:-100});assert.equal(value('azimuth'),175);
 node.onConnectionsChange();assert.match(notice.textContent,/azimuth/);
 assert.equal(node.onExecuted({camera_caption:['server caption']}),'executed');assert.equal(output.textContent,'server caption');
 node.widgets.find(w=>w.name==='distance').callback();assert.notEqual(output.textContent,'server caption');
 node.inputs=[];toolbar.children.at(-1).onclick();
 assert.deepEqual(node.widgets.filter(w=>w.serialize!==false).map(w=>[w.name,w.value]),before);
 toolbar.children.at(-2).onclick();assert.equal(value('random_mode'),'balanced');assert.ok(Number.isInteger(value('random_seed')));
 const sampled=sandbox.randomCamera('balanced',value('random_seed'));
 click(264,164);
 assert.equal(value('random_mode'),'off');assert.equal(value('azimuth'),90);assert.equal(value('elevation'),sampled.elevation);assert.equal(value('distance'),sampled.distance);assert.equal(value('roll'),sampled.roll);
 node.widgets.find(w=>w.name==='random_mode').value='full';toolbar.children.at(-2).onclick();assert.equal(value('random_mode'),'full');
 node.onExecuted({camera_caption:['random server caption'],camera_values:[{azimuth:10,elevation:20,distance:.3,roll:2}]});
 assert.equal(output.textContent,'random server caption');
 const beforeOrbit=node.widgets.map(w=>w.value);
 orbit.onclick();
 assert.equal(orbit.attributes['aria-pressed'],'true');
 assert.equal(output.textContent,'random server caption');
 assert.deepEqual(node.widgets.map(w=>w.value),beforeOrbit);
 click(300,160);assert.equal(value('random_mode'),'full');
 canvas.onpointerdown(event(300,160));
 canvas.onpointermove(event(400,140,2));assert.equal(value('random_mode'),'full');
 canvas.onpointermove(event(400,140));
 assert.equal(value('random_mode'),'off');
 assert.deepEqual(['azimuth','elevation','distance','roll'].map(value),[75,33,.3,2]);
 canvas.onpointerup(event(400,140));
 sandbox.setCameraValues(node,{azimuth:175,elevation:80});
 canvas.onpointerdown(event(300,160));canvas.onpointermove(event(320,100));
 assert.equal(value('azimuth'),-172);assert.equal(value('elevation'),90);
 canvas.onpointermove(event(320,120));assert.equal(value('elevation'),77);
 dials.onclick();assert.equal(canvas.captured,undefined);
 canvas.onpointermove(event(340,140));assert.equal(value('azimuth'),-172);
 assert.equal(value('elevation'),77);assert.equal(dials.attributes['aria-pressed'],'true');
 node.properties.rs_camera_control_mode='orbit';
 node.onConfigure();assert.equal(orbit.attributes['aria-pressed'],'true');
 node.inputs=[{name:'azimuth',link:1}];node.onConnectionsChange();
 node.onExecuted({camera_values:[{azimuth:90,elevation:0,distance:.3,roll:2}]});
 canvas.onpointerdown(event(300,160));canvas.onpointermove(event(340,140));canvas.onpointercancel(event(340,140));
 assert.equal(value('azimuth'),-172);assert.equal(value('elevation'),13);
 assert.ok(drawnText.some(s=>s.includes('(90° / 13°)')));
 node.inputs=[];node.onConnectionsChange();dials.onclick();
 toolbar.children.at(-1).onclick();assert.equal(value('random_mode'),'off');
 node.onExecuted({camera_regions:[[{id:1,x:.3,y:.5,mask:{width:2,height:2,bits:'wA=='}},{id:2,x:.7,y:.5,box:[.5,.2,.8,.8]},{id:3,x:.5,y:.1,kind:'text',box:[.1,0,.9,.2]}]],camera_layout:[{mode:'distance_and_roll',aspect:1.5}]});
 assert.match(layoutNotice.textContent,/distance|거리|距離|距离/);assert.equal(layoutCanvas.height,427);
 sandbox.setCameraValues(node,{layout_sync:'distance_and_roll',canvas_aspect:2,distance:.8,roll:25});
 assert.equal(layoutCanvas.height,320);
 sandbox.setCameraValues(node,{layout_sync:'perspective',azimuth:45,elevation:25});assert.match(layoutNotice.textContent,/perspective|원근|遠近|透[视視]/);
 sandbox.setCameraValues(node,{enabled:false});editor.render();
 assert.equal(node.onConfigure(),'configured');
 vm.runInNewContext(source,{app,document:{createElement:element},console});
 console.log('Camera: Python/JS curve and trained-view parity, dial/orbit interaction, linked controls and serialization passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
