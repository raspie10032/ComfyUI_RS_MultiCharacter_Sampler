const fs = require('fs'), vm = require('vm'), assert = require('node:assert/strict');
const presets = JSON.parse(fs.readFileSync('web/model_presets.json'));
const source = fs.readFileSync('web/app_graph.js','utf8').replaceAll('export ','') + '\nthis.subject={Workspace,widget,setValue,ancestorPrompt,executionNodes};';
const context = {structuredClone}; vm.createContext(context); vm.runInContext(source,context);
const {Workspace,widget,setValue,ancestorPrompt,executionNodes} = context.subject;
class Graph {
  constructor(){this.extra={};this.nodes=[];this.links={};this.serial=0;this.next=0;}
  add(n){n.id=++this.next;n.graph=this;this.nodes.push(n);}
  getNodeById(id){return this.nodes.find(n=>n.id===id);}
  change(){}
}
// Deliberately small node doubles test routing state, not native socket types.
// Typed closures are additionally checked against the installed /object_info.
function createNode(type) {
  const values = Object.assign({}, ...presets.map(p=>p.settings), {
    character_count:2,scene_json:'{"width":1024,"height":1024,"people":[]}',drawing:'{"version":1,"width":768,"height":1024,"layers":{}}',
    width:1024,height:1024,cfg:4,prompt:'keep common prompt',value:'',lora_name:'None',name:'anima_3dpose_6200.safetensors'
  });
  for(let i=1;i<=10;i++) Object.assign(values,{['character'+i+'_kind']:'character',['character'+i+'_enable']:true,['character'+i+'_lora']:'None'});
  const inputs=['building_pipe','base_prompt','model','clip','vae','images','image','scene_json','model_patch','character_pipe','detectors','tagger',...Array.from({length:10},(_,i)=>'character'+(i+1))];
  return {type,widgets:Object.entries(values).map(([name,value])=>({name,value,options:{values:name==='name'?['anima_3dpose_6200.safetensors']:undefined}})),
    inputs:inputs.map(name=>({name,link:null})),outputs:['result','pose_image','scene_json','character_pipe'].map(name=>({name})),
    disconnectInput(i){delete this.graph.links[this.inputs[i].link];this.inputs[i].link=null;},
    connect(a,to,b){to.disconnectInput(b);const id=++this.graph.serial;this.graph.links[id]={origin_id:this.id,origin_slot:a,target_id:to.id,target_slot:b};to.inputs[b].link=id;}};
}
const graph=new Graph(),w=new Workspace(graph,createNode,presets).initialize();
function model(profile,preset,pose){return {id:profile,name:profile,profile,preset,category:'checkpoints',missing:[],capabilities:{family:profile,reference:true,layout:profile==='moss'?'moss_native':'regional',pose,pose_reference:false,pose_progressive:false}};}
const anima=model('anima','anima_points','lllite'),moss=model('moss','moss_base','scene_adapter');
function closure(){const prompt={};for(const n of graph.nodes){const inputs=Object.fromEntries(n.widgets.map(w=>[w.name,w.value]));for(const input of n.inputs)if(input.link!=null){const l=graph.links[input.link];inputs[input.name]=[String(l.origin_id),l.origin_slot];}prompt[n.id]={class_type:n.type,inputs};}return ancestorPrompt(prompt,w.node('save').id);}
w.select(anima);w.state.globalLora=true;setValue(w.sample(),'cfg',3.75);const scene=widget(w.node('pose'),'scene_json').value;
w.state.camera=true;w.route();assert.equal(widget(w.node('common_prompt'),'value').value,widget(w.sample(),'prompt').value,'camera must receive the common scene caption');
w.select(moss);assert.equal(w.state.globalLora,false);setValue(w.sample(),'cfg',1.5);
w.select(anima);assert.equal(w.state.globalLora,true);assert.equal(widget(w.sample(),'cfg').value,3.75);assert.equal(widget(w.node('pose'),'scene_json').value,scene);
w.state.detail=true;w.route();assert(Object.values(closure()).some(n=>n.class_type==='RSMultiCharacterTaggerLoader'),'multiple characters automatically require matching');
setValue(w.node('detail'),'cfg',3.5);w.select(moss);assert.equal(widget(w.node('detail'),'cfg').value,presets.find(p=>p.id===moss.preset).settings.cfg);
w.select(anima);assert.equal(widget(w.node('detail'),'cfg').value,3.5,'detail settings restore for their model');
setValue(w.node('prompt'),'character_count',1);w.route();assert(!Object.values(closure()).some(n=>n.class_type==='RSMultiCharacterTaggerLoader'),'unused matching is excluded from one-character execution');
w.state.detail=false;w.state.refs={3:true};w.route();assert(!Object.values(closure()).some(n=>n.class_type==='RSMultiCharacterReference'),'hidden slots must not execute');
assert.equal(executionNodes(graph,w.node('save').id).length,Object.keys(closure()).length,'widget callbacks follow only active ancestors');
w.state.refs={1:true};w.state.pose=true;w.select(moss);assert(w.issues().length,'unsupported pose/reference combination must block generation');
assert(w.state.refs[1] && w.state.pose,'conflicting user work must remain available');
w.state.refs={};w.state.progressive=true;w.route();assert(w.issues().length);
w.state.pose=false;w.state.progressive=false;w.state.masks=true;setValue(w.node('masks'),'drawing','{"layers":{}}');assert(w.issues().some(message=>message.includes('영역을 그리')));
const persisted=graph.extra.rs_workspace;assert.equal(new Workspace(graph,createNode,presets).state,persisted);
console.log('App graph: model restoration, mandatory tagger, inactive-slot exclusion, combination gates and persistence passed.');
