const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
let extension;
const src=fs.readFileSync('web/character_builder.js','utf8').replace(/^import[^\n]*\n/gm,'').replaceAll('export function','function');
const sandbox={queueMicrotask,maskPreview:node=>node.testMask??null,rememberMaskPreview(){},app:{registerExtension(e){extension=e;}}};vm.runInNewContext(src,sandbox);
const previewSandbox={app:{},api:{apiURL:s=>s},URLSearchParams};
vm.runInNewContext(fs.readFileSync('web/mask_preview.js','utf8').replace(/^import[^\n]*\n/gm,'').replaceAll('export function','function'),previewSandbox);
sandbox.placedSupport=previewSandbox.placedSupport;
const {collectSlots,centersFor}=sandbox;
function make(type,settings,upstream=null){return {type,widgets:Object.entries(settings).map(([name,value])=>({name,value})),inputs:[{name:'building_pipe'},{name:'character1'},{name:'character2'}],getInputNode(i){return i===0?upstream:type==='RSMultiCharacterPrompt'?{}:null;}};}
const actions=[['RSMultiCharacterPrompt',{character_count:2}],['RSMultiCharacterPosition',{character_count:2,character1_x:.25,character2_x:.75}],['RSMultiCharacterLoRA',{character_count:2}]];
const build=list=>list.reduce((node,[type,settings])=>make(type,settings,node),null);
assert.deepEqual(JSON.parse(JSON.stringify(collectSlots(build(actions)))),JSON.parse(JSON.stringify(collectSlots(build([...actions].reverse())))));
assert.equal(JSON.stringify(centersFor(collectSlots(build([actions[0]])).slots)),JSON.stringify([[.25,.5],[.75,.5]]));
const root=build(actions),bypass=make('RSMultiCharacterPosition',{character_count:1,character1_x:.9},root);bypass.mode=4;
assert.equal(collectSlots(bypass).slots[0].x,.25);
assert.equal(collectSlots(make('RSMultiCharacterPrompt',{character_count:1},root)).slots.length,1);
assert.equal(collectSlots(make('RSMultiCharacterPrompt',{character_count:2,character2_enable:false},root)).slots.length,1);
const mask=make('RSMultiCharacterMask',{character_id:1,enabled:true},build([actions[0]]));
const masked=collectSlots(mask);
assert.equal(masked.slots[0].masked,true);assert.equal(masked.unknown,false);
mask.testMask={width:2,height:2,data:[1,0,1,0],center:[.25,.5]};
assert.equal(collectSlots(mask).slots[0].maskSupport,mask.testMask);
assert.equal(JSON.stringify(centersFor(collectSlots(mask).slots)),JSON.stringify([[.25,.5],[.5,.5]]));
assert.equal(JSON.stringify(centersFor(masked.slots)),JSON.stringify([[.5,.5],[.5,.5]]));
const cleared=collectSlots(make('RSMultiCharacterMask',{character_id:1,enabled:false},mask));
assert.equal(cleared.slots[0].masked,false);
assert.equal(JSON.stringify(centersFor(cleared.slots)),JSON.stringify([[.25,.5],[.75,.5]]));
const positioned=make('RSMultiCharacterPosition',{character_count:2,mask_transforms:'{"1":[0.5,0,1]}'},mask);
assert.deepEqual(Array.from(collectSlots(positioned).slots[0].maskSupport.data),[0,1,0,1]);
assert.equal(collectSlots(positioned).slots[0].maskSupport,collectSlots(positioned).slots[0].maskSupport); // Cached raster, not per-frame allocation.
assert.equal(collectSlots(positioned).slots[0].maskOriginal,mask.testMask);
const before=make('RSMultiCharacterMask',{character_id:1,enabled:true},make('RSMultiCharacterPosition',{character_count:2,mask_transforms:'{"1":[0.5,0,1]}'},build([actions[0]])));
before.testMask=mask.testMask;
assert.deepEqual(Array.from(collectSlots(before).slots[0].maskSupport.data),Array.from(collectSlots(positioned).slots[0].maskSupport.data));
class Node {
 constructor(type='RSMultiCharacterPosition') {this.type=type;this.inputs=[];this.widgets=[{name:'character_count',value:2},...Array.from({length:10},(_,i)=>['geometry','x','y','width','height'].map(name=>({name:`character${i+1}_${name}`,value:name==='geometry'?'point':.5}))).flat()].map(w=>({...w,type:'number',computeSize:()=>[300,20]}));this.size=[340,200];}
 addCustomWidget(w){this.widgets.push(w);}computeSize(){return[340,200];}setSize(s){this.size=s;}setDirtyCanvas(){}addInput(name,type){this.inputs.push({name,type,link:null});}removeInput(i){this.inputs.splice(i,1);}
}
(async()=>{
 await extension.beforeRegisterNodeDef(Node,{name:'RSMultiCharacterPosition'});
 const n=new Node();n.onNodeCreated();
 const get=name=>n.widgets.find(w=>w.name===name);
 assert.equal(get('character1_width').hidden,true);assert.equal(get('character2_x').hidden,undefined);assert.equal(get('character3_x').hidden,true);
 get('character2_geometry').value='box';get('character2_geometry').callback();assert.equal(get('character2_width').type,'number');assert.equal(get('character1_width').hidden,true);
 get('character_count').value=5;get('character_count').callback();assert.equal(get('character5_x').type,'number');
 assert.equal(get('rs_mc_build_layout').serializeValue(),undefined);
 class LoRA extends Node {constructor(){super('RSMultiCharacterLoRA');this.widgets=[{name:'character_count',value:2},{name:'lora_application_mode',value:'normal'},...Array.from({length:10},(_,i)=>({name:`character${i+1}_lora`,value:'None'}))];}}
 await extension.beforeRegisterNodeDef(LoRA,{name:'RSMultiCharacterLoRA'});
 const lora=new LoRA();lora.onNodeCreated();
 const help=lora.widgets.find(w=>w.name==='rs_mc_lora_mode_help');
 assert.ok(help);assert.equal(lora.widgets.at(-1),help);
 assert.equal(help.serialize,false);assert.equal(help.options.serialize,false);
 assert.equal(help.serializeValue(),undefined);
 let locale='en';sandbox.app.extensionManager={setting:{get:()=>locale}};
 for(const [language,normal,precision] of [['en','Normal','Precision'],['ko','일반 적용','정밀 적용'],['ja','通常適用','精密適用']]) {
  locale=language;
  for(const [mode,heading] of [['normal',normal],['precision',precision]]) {
   lora.widgets[1].value=mode;lora.widgets[1].callback();
   const lines=[];
   const ctx={save(){},restore(){},fillRect(){},fillText(text,x,y,maxWidth){lines.push({text,x,y,maxWidth});}};
   const height=help.computeSize(340)[1];
   help.draw(ctx,lora,340,0);
   assert.ok(lines[0].text.startsWith(heading));
   assert.ok(lines.every(line=>line.y<height && line.x>=0 && line.maxWidth===308));
   assert.ok(sandbox.loraModeHelp(lora).some(line=>/Detailer|디테일러/.test(line)));
   assert.ok(help.computeSize(600)[1]<=height);
  }
 }
 lora.widgets[1].value='normal';
 for(const count of [1,10,2]) {
  lora.widgets[0].value=count;lora.widgets[0].callback();
  assert.equal(lora.widgets[1].value,'normal');
  assert.equal(lora.widgets[1].hidden,undefined);
 }
 class Prompt extends Node {constructor(){super('RSMultiCharacterPrompt');this.widgets=[{name:'character_count',value:2},...Array.from({length:10},(_,i)=>({name:`character${i+1}_kind`,value:'character'}))];this.inputs=[{name:'building_pipe',link:null},...Array.from({length:10},(_,i)=>['','_text'].map(suffix=>({name:`character${i+1}${suffix}`,type:'STRING',link:null}))).flat()];}}
 await extension.beforeRegisterNodeDef(Prompt,{name:'RSMultiCharacterPrompt'});
 const p=new Prompt();p.onNodeCreated();assert.equal(p.inputs.filter(i=>i.type==='STRING').length,2);
 const shared=p.inputs.find(i=>i.name==='character2');shared.link=100;
 const kind=p.widgets.find(w=>w.name==='character2_kind');
 for(const value of ['text','character','text','character']) {
  kind.value=value;kind.callback();
  assert.equal(p.inputs.filter(i=>i.type==='STRING').length,2);
  assert.equal(p.inputs.find(i=>i.name==='character2'),shared);
  assert.equal(shared.link,100);
  assert.equal(p.inputs.some(i=>i.name.endsWith('_text')),false);
 }
 p.inputs.find(i=>i.name==='character2').link=100;p.widgets[0].value=1;p.widgets[0].callback();
 assert.equal(p.inputs.find(i=>i.name==='character2').link,100); // Never destroy a saved connection.
 p.widgets[0].value=5;p.widgets[0].callback();assert.equal(p.inputs.filter(i=>i.type==='STRING').length,5);
 // A saved old two-input row keeps the literal word connection after migration.
 const old=new Prompt();old.widgets.find(w=>w.name==='character2_kind').value='text';
 old.inputs.find(i=>i.name==='character2').link=17;
 old.inputs.find(i=>i.name==='character2_text').link=18;
 old.graph={links:{18:{origin_id:42,origin_slot:0}},getNodeById(id){assert.equal(id,42);return {connect(slot,target,index){assert.equal(slot,0);target.inputs[index].link=19;}};}};
 old.onConfigure();old.onGraphConfigured();await Promise.resolve();
 assert.equal(old.inputs.filter(i=>i.type==='STRING').length,2);
 assert.equal(old.inputs.find(i=>i.name==='character2').link,19);
 assert.equal(old.inputs.some(i=>i.name.endsWith('_text')),false);
 console.log('Role tables, one shared STRING across kind changes, legacy migration, inactive slots and preview controls passed');
})();
