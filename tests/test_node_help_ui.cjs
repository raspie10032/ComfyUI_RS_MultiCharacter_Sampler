const fs = require('fs'), vm = require('vm'), assert = require('node:assert/strict');
const source = require("./ui_source.cjs")('web/node_help.js').replace(/^import[^\n]*\n/gm, '').replaceAll('export function', 'function');
let extension, lang = 'en';
const app = {registerExtension(e) { extension = e; }, extensionManager: {setting: {get() { return lang; }}}};
const sandbox = {app}; vm.runInNewContext(source, sandbox);
const specs = {
  RSAnimaReferenceAdapter: {reference_guidance:1},
  RSAnimaCharacterReference: {character_id:1,strength:1,enabled:true},
  RSMultiCharacterPrompt: {character_count:2,character1_kind:'character',character2_kind:'text'},
  RSMultiCharacterPosition: {character_count:2,character1_geometry:'point',character2_geometry:'box'},
  RSMultiCharacterFinalize: {},
  RSMultiCharacterMask: {character_id:1,enabled:true,margin:24,threshold:.5},
  RSMultiCharacterProgressiveSampler: {width:1152,height:1728,steps:30,start_scale:.67,layout_method:"regional",autosave:true},
  RSMultiCharacterSampler: {layout_method:'regional',use_image_settings:false,autosave:true,save_format:'PNG',sampler_name:'euler',scheduler:'simple'},
  RSMultiCharacterLoadImage: {image:'example.png'},
  RSMultiCharacterDetailer: {show_advanced:false,autosave:true,save_format:'PNG'},
  RSMultiCharacterTaggerLoader: {device:'auto',model_name:'WD ViT v3',batch_size:4},
  RSMultiCharacterPrompts: {layout_mode:'points'},
  RSMultiCharacterInteraction: {preset:'baseline',delay_steps:6,decrement:.2},
};
function makeClass(type, settings) { return class {
  constructor() { this.type=type;this.widgets=Object.entries(settings).map(([name,value])=>({name,value,type:'combo',options:{},callback(...args){this.lastArgs=args;return 42;}}));this.inputs=[];this.size=[340,200];this.configures=0; }
  addCustomWidget(w) { this.widgets.push(w); }
  computeSize() { return [340,100+this.widgets.reduce((n,w)=>n+(w.computeSize?.(this.size[0])[1]??20),0)]; }
  setSize(size) { this.size=size;this.onResize?.(size); }
  setDirtyCanvas() {}
  onConfigure() { this.configures++; return 'configured'; }
}; }
const get=(node,name)=>node.widgets.find(w=>w.name===name);
const choose=(node,name,value)=>{const w=get(node,name);w.value=value;return w.callback?.call(w,'event');};
const help=node=>sandbox.nodeHelp(node).join('\n');
(async()=>{
  const nodes={};
  for (const [type,settings] of Object.entries(specs)) {
    const Node=makeClass(type,settings);await extension.beforeRegisterNodeDef(Node,{name:type});
    const node=nodes[type]=new Node();node.onNodeCreated();
    const before=node.widgets.filter(w=>w.serialize!==false).map(w=>[w.name,w.value]);
    const panel=get(node,'rs_mc_node_help');assert.ok(panel);assert.equal(node.widgets.at(-1),panel);
    assert.equal(panel.serialize,false);assert.equal(panel.options.serialize,false);assert.equal(panel.serializeValue(),undefined);
    for (const locale of ['en','ko','ja','zh','zh-TW']) {
      lang=locale;node.onDrawForeground();
      assert.ok(help(node).length>(['RSMultiCharacterInteraction','RSAnimaReferenceAdapter','RSAnimaCharacterReference'].includes(type)?40:80));
      for (const width of [340,600,1000]) {
        node.size[0]=width;node.onResize();
        const draw=[];panel.draw({save(){},restore(){},fillRect(){},fillText(text,x,y,max){draw.push({text,x,y,max});}},node,width,0);
        assert.ok(draw.every(line=>line.y<panel.computeSize(width)[1]&&line.max===width-32));
        assert.ok(panel.computeSize(600)[1]<=panel.computeSize(340)[1]);
      }
    }
    assert.equal(node.onConfigure(),'configured');assert.equal(node.configures,1);
    node.onNodeCreated();assert.equal(node.widgets.filter(w=>w.name==='rs_mc_node_help').length,1);
    assert.deepEqual(node.widgets.filter(w=>w.serialize!==false).map(w=>[w.name,w.value]),before);
  }
  lang='en';
  const interaction=nodes.RSMultiCharacterInteraction;
  assert.match(help(interaction),/Baseline: no extra/);
  choose(interaction,'preset','delay3');assert.match(help(interaction),/decay follows the sampler/);
  choose(interaction,'preset','custom');assert.match(help(interaction),/Custom: use/);
  interaction.inputs=[{name:'preset',link:1}];interaction.onConnectionsChange();
  assert.match(help(interaction),/resolved at execution/);
  const prompt=nodes.RSMultiCharacterPrompt;
  assert.match(help(prompt),/Character: 1 \/ Text: 2/);assert.match(help(prompt),/Text needs a box/);
  assert.equal(choose(prompt,'character2_kind','character'),42);assert.deepEqual(get(prompt,'character2_kind').lastArgs,['event']);
  assert.match(help(prompt),/Character: 1, 2 \/ Text: —/);assert.doesNotMatch(help(prompt),/Text needs a box/);
  choose(prompt,'character_count',1);assert.match(help(prompt),/Character: 1 \/ Text: —/);
  const sampler=nodes.RSMultiCharacterSampler;
  choose(sampler,'use_image_settings',true);assert.match(help(sampler),/Image settings ON/);
  choose(sampler,'layout_method','moss_native');assert.match(help(sampler),/requires MOSS and box/);
  for (const [locale,notice] of [['en',/Masks become enclosing rectangles/],['ko',/마스크는 최종 배치의 외곽 사각형/],['ja',/マスクは最終配置の外接矩形/],['zh',/外接矩形/],['zh-TW',/外接矩形/]]) {
    lang=locale;assert.match(help(sampler),notice);
    choose(sampler,'layout_method','regional');assert.doesNotMatch(help(sampler),notice);
    choose(sampler,'layout_method','moss_native');
  }
  lang='en';
  choose(sampler,'save_format','WebP lossy');assert.match(help(sampler),/Lossy WebP/);
  choose(sampler,'autosave',false);assert.match(help(sampler),/Autosave OFF/);assert.doesNotMatch(help(sampler),/Lossy WebP/);
  const tagger=nodes.RSMultiCharacterTaggerLoader;
  assert.match(help(tagger),/not character count/);
  choose(tagger,'device','cpu');assert.match(help(tagger),/CPU selected/);
  choose(tagger,'model_name','PixAI Tagger v1.0');assert.match(help(tagger),/batch_size=1/);
  tagger.inputs=[{name:'model_name',link:1}];tagger.onConnectionsChange();assert.match(help(tagger),/resolved at execution/);
  assert.match(help(nodes.RSMultiCharacterDetailer),/folded/);
  choose(nodes.RSMultiCharacterDetailer,'show_advanced',true);assert.match(help(nodes.RSMultiCharacterDetailer),/are visible/);
  assert.ok(sandbox.helpLines(['A'.repeat(200)],340).length>2);
  // Existing LoRA and detector panels must not be duplicated.
  for(const name of ['RSMultiCharacterLoRA','RSMultiCharacterDetectionLoader','OtherExtension']) {
    const Node=makeClass(name,{});await extension.beforeRegisterNodeDef(Node,{name});assert.equal(Node.prototype.onNodeCreated,undefined);
  }
  // Extension registration order must not hide help or lose socket/visibility callbacks.
  for(const order of [['node_help','detailer'],['detailer','node_help'],['node_help','character_builder'],['character_builder','node_help']]) {
    const extensions=[];
    const host={queueMicrotask,app:{...app,registerExtension(e){extensions.push(e);}},ComfyWidgets:{STRING(node,name){const widget={name,type:'text',options:{},inputEl:{}};node.widgets.push(widget);return {widget};}}};
    for(const file of order) vm.runInNewContext(require("./ui_source.cjs")(`web/${file}.js`).replace(/^import[^\n]*\n/gm,'').replaceAll('export function','function'),vm.createContext({...host}));
    const type=order.includes('detailer')?'RSMultiCharacterDetailer':'RSMultiCharacterPrompt';
    const Node=makeClass(type,{...specs[type],character_count:2,show_advanced:false,steps:20});
    Node.prototype.addInput=function(name,type){this.inputs.push({name,type});};Node.prototype.removeInput=function(i){this.inputs.splice(i,1);};
    for(const e of extensions) await e.beforeRegisterNodeDef(Node,{name:type});
    const node=new Node();node.onNodeCreated();node.onConfigure();await Promise.resolve();
    const panel=get(node,'rs_mc_node_help');assert.ok(panel);assert.notEqual(panel.hidden,true);assert.equal(panel.type,'rs_mc_display');
    if(type==='RSMultiCharacterDetailer') {assert.equal(get(node,'steps').hidden,true);choose(node,'show_advanced',true);assert.equal(get(node,'steps').hidden,undefined);}
    else {choose(node,'character_count',3);assert.ok(node.inputs.some(i=>i.name==='character3'));}
  }
  console.log('All node help: five locales, selection changes, bounds, serialization, callback preservation and extension order passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
