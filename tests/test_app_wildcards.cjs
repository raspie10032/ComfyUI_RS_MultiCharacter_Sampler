const fs=require('fs'), vm=require('vm'), assert=require('node:assert/strict');
const graph=fs.readFileSync('web/app_graph.js','utf8').replaceAll('export ','');
const wildcardSource=fs.readFileSync('web/app_wildcards.js','utf8');
let context;
for(const newline of ['\n','\r\n']) {
 const wc=wildcardSource.replace(/\r?\n/g,newline).replace(/^import[^\r\n]*(?:\r?\n|$)/gm,'').replaceAll('export ','');
 context={structuredClone};vm.createContext(context);vm.runInContext(graph+'\n'+wc+'\nthis.subject={promptFields,restoreTemplates,resolvePrompts,expandedPrompt};',context);
}
const {promptFields,restoreTemplates,resolvePrompts,expandedPrompt}=context.subject;
const node=values=>({widgets:Object.entries(values).map(([name,value])=>({name,value}))});
const nodes={sampler:node({prompt:'__scenes__',negative_prompt:'{bad|ugly}',seed:123}),prompt:node({character1_enable:true,character2_enable:true,character2_kind:'text',character3_enable:false}),text1:node({value:'__fabe__'}),text2:node({value:'MENU {A|B}'}),text3:node({value:'__missing__'})};
let routed=0;
const w={state:{},sample:()=>nodes.sampler,node:key=>nodes[key],count:()=>3,route:()=>{routed++}};
(async()=>{
assert.deepEqual(Array.from(promptFields(w),f=>f.key),['prompt','negative','character1']);
const fetch=async(_url,options)=>{
 const data=JSON.parse(options.body);assert.equal(data.seed,123);assert.equal(data.texts.character1,'__fabe__');
 assert(!Object.hasOwn(data.texts,'character2'));assert(!Object.hasOwn(data.texts,'character3'));
 return {ok:true,json:async()=>({texts:{prompt:'cafe',negative:'bad',character1:'Barbara'}})};
};
const expansion=await resolvePrompts(w,fetch);
const full=await expandedPrompt(w,expansion,async()=>({node:structuredClone(nodes),extra:w.state}));
assert.equal(full.node.text1.widgets[0].value,'Barbara');
assert.equal(nodes.text1.widgets[0].value,'__fabe__');
assert.equal(full.extra.wildcardLast.templates.character1,'__fabe__');
assert.equal(nodes.text2.widgets[0].value,'MENU {A|B}');
assert.equal(routed,2);
// graphToPrompt may return reactive workflow.extra / widget / extension values.
// Verify a detached snapshot is captured before templates are restored in finally.
const reactiveExpansion=new Proxy({...expansion,texts:new Proxy(expansion.texts,{})},{});
assert.throws(()=>structuredClone(reactiveExpansion),{name:'DataCloneError'});
const metadata=new Proxy({name:'한글 日本語',coords:new Proxy([0.25,0.75],{}),seed:9007199254740991},{});
let serialized;
const reactiveFull=await expandedPrompt(w,reactiveExpansion,async()=>{
 serialized=new Proxy({workflow:{extra:new Proxy({workspace:w.state,metadata},{})},output:{'1':{inputs:{text:nodes.text1.widgets[0].value}}}},{});
 return serialized;
});
assert.equal(reactiveFull.output['1'].inputs.text,'Barbara');
assert.equal(nodes.text1.widgets[0].value,'__fabe__');
assert.equal(reactiveFull.workflow.extra.workspace.wildcardLast.templates.character1,'__fabe__');
assert.equal(reactiveFull.workflow.extra.metadata.name,'한글 日本語');
assert.equal(reactiveFull.workflow.extra.metadata.seed,9007199254740991);
metadata.coords[0]=0.9;w.state.wildcardLast.texts.character1='changed after queue';
assert.equal(reactiveFull.workflow.extra.metadata.coords[0],0.25);
assert.equal(reactiveFull.workflow.extra.workspace.wildcardLast.texts.character1,'Barbara');
const cyclic={};cyclic.self=cyclic;
await assert.rejects(expandedPrompt(w,expansion,async()=>cyclic),/circular|cyclic/i);
assert.equal(nodes.text1.widgets[0].value,'__fabe__','snapshot failure also restores source templates');
await assert.rejects(expandedPrompt(w,expansion,async()=>{throw Error('serialize failed')}),/serialize failed/);
assert.equal(nodes.text1.widgets[0].value,'__fabe__','failed generation restores templates');
nodes.text1.widgets[0].value='Barbara';restoreTemplates(w);assert.equal(nodes.text1.widgets[0].value,'__fabe__','PNG restores source template');
nodes.text1.widgets[0].value='manual graph edit';restoreTemplates(w);assert.equal(nodes.text1.widgets[0].value,'manual graph edit');
w.state.wildcards=false;await resolvePrompts(w,()=>{throw Error('disabled must skip IO')});
w.state.wildcards=true;
await assert.rejects(resolvePrompts(w,async()=>({ok:false,json:async()=>({error:'missing wildcard'})})),/missing wildcard/);
console.log('App wildcards: active character scope, typography exclusion, seeded resolution, serialized provenance, template recovery and failure restoration passed.');
})().catch(error=>{console.error(error);process.exitCode=1});
