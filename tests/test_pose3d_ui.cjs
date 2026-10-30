const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const {randomUUID}=require('crypto');
class Element{
 constructor(tag){this.tag=tag;this.style={};this.children=[];this.files=[];this.width=240;}
 append(...children){this.children.push(...children);}setAttribute(){}focus(){this.focused=true;}click(){this.clicked=true;}remove(){this.removed=true;}
 getContext(){return {clearRect(){},fillRect(){},fillText(){}};}
}
let extension,uploadCalls=0,queueCalls=0,historyCalls=0,removedListeners=0,queued,history,preview;
const listeners=new Map(),windowListeners=new Map();
const sandbox={Blob,FormData,URL,URLSearchParams,AbortController,DOMException,Uint8Array,crypto:{randomUUID},
 location:{origin:'http://localhost:8188'},chineseLocale:()=>false,chineseText:t=>t,
 app:{registerExtension:e=>extension=e,extensionManager:{setting:{get:()=> 'en'}}},
 api:{addEventListener:(type,fn)=>listeners.set(type,fn),removeEventListener:()=>{removedListeners++;listeners.clear();},
 async queuePrompt(n,p){queueCalls++;assert.equal(n,-1);assert.deepEqual(Object.values(p.output).map(x=>x.class_type),['LoadImage','RSImageToPose3D']);queued=p;return {prompt_id:'my-import'};},
 async fetchApi(path,options){
  if(path==='/upload/image'){uploadCalls++;return {ok:true,json:async()=>({name:'person.png',subfolder:'RS_PoseImports'})};}
  if(path.startsWith('/history/')){historyCalls++;return {ok:true,json:async()=>await history()};}
  if(path.endsWith('/preview'))return {ok:true,json:async()=>preview};
  throw Error(path);
 }},
 document:{createElement:tag=>new Element(tag),body:new Element('body')},
 window:{addEventListener:(t,f)=>windowListeners.set(t,f),removeEventListener:t=>windowListeners.delete(t)},
 setTimeout:()=>1,clearTimeout(){},
};
vm.createContext(sandbox);
let source=fs.readFileSync('web/pose3d.js','utf8').replace(/^import[^\n]*\n/gm,'').replaceAll('export function','function').replaceAll('import.meta.url',"'http://localhost:8188/extensions/rs/pose3d.js'");
vm.runInContext(source,sandbox);
class Node{
 constructor(){this.widgets=[{name:'scene_json',value:JSON.stringify({version:2,people:[{id:1}],camera:{original:true}})}];this.inputs=[];this.graph={change:()=>this.changed=true,setDirtyCanvas(){}};}
 addWidget(type,name,value,callback){const w={type,name,value,callback};this.widgets.push(w);return w;}
 addDOMWidget(name,type,element){const w={name,type,element};this.widgets.push(w);return w;}
}
const file=new Blob(['test image'],{type:'image/png'}),imported={version:2,people:[{id:1,joints:{head:[1,2,3]}}],width:380,height:280,camera:{source:true}};
function goodHistory(){const id=Object.keys(queued.output).find(x=>x.startsWith('rs_pose_estimate_'));return {'my-import':{outputs:{[id]:{rs_pose_image:[{pose:{joints:{}},scene:imported}]}},status:{completed:true}}};}
async function run(){
 await extension.beforeRegisterNodeDef(Node,{name:'RSMultiCharacterPose3D'});
 const node=new Node();node.onNodeCreated();assert(node.widgets.some(w=>w.name==='pose3d_import'&&w.serialize===false));
 history=goodHistory;await sandbox.importImage(node,file);
 assert.equal(node.changed,true);assert.deepEqual(JSON.parse(node.widgets[0].value),imported);assert.equal(sandbox.document.body.children.length,1);assert.equal(removedListeners,1);
 const modal=sandbox.document.body.children[0];const frame=modal.children[0].children[0];assert.equal(frame.tag,'iframe');
 const posts=[];frame.contentWindow={postMessage:message=>posts.push(message)};
 const receive=windowListeners.get('message'),token=frame.src.split('#')[1];
 const event=data=>({source:frame.contentWindow,origin:'http://localhost:8188',data:{...data,token}});
 await receive(event({type:'rs-pose3d-ready'}));assert.equal(JSON.stringify(posts[0].scene),JSON.stringify(imported));
 const message={type:'rs-pose3d-image-request',requestId:randomUUID(),file};
 const beforeBad=queueCalls;await receive({...event(message),origin:'https://wrong.example'});assert.equal(queueCalls,beforeBad);
 await receive(event(message));assert.equal(posts.at(-1).type,'rs-pose3d-image-result');assert.equal(posts.at(-1).requestId,message.requestId);
 const applied={...imported,width:512};await receive(event({type:'rs-pose3d-apply',scene:applied}));assert.equal(JSON.parse(node.widgets[0].value).width,512);
 const second=new Node();second.onNodeCreated();let complete;
 history=()=>new Promise(resolve=>complete=resolve);
 const pending=sandbox.importImage(second,file);await new Promise(setImmediate);
 const oldCalls=queueCalls;await sandbox.importImage(second,file);assert.equal(queueCalls,oldCalls,'duplicate import blocked');
 second.widgets[0].value='edited';complete(goodHistory());await pending;
 assert.equal(second.widgets[0].value,'edited');assert(second.widgets.find(w=>w.name==='pose3d_status').element.textContent.includes('Scene changed'));
 const linked=new Node();linked.inputs=[{name:'scene_json',link:5}];linked.onNodeCreated();await sandbox.importImage(linked,file);assert.equal(queueCalls,oldCalls);
 const failed=new Node();failed.onNodeCreated();history=()=>({'my-import':{status:{messages:[['execution_error',{exception_message:'No person detected'}]]}}});
 await sandbox.importImage(failed,file);assert(failed.widgets.find(w=>w.name==='pose3d_status').element.textContent.includes('No person detected'));assert.equal(failed.changed,undefined);
 await sandbox.importImage(failed,new Blob(['no'],{type:'text/plain'}));assert(failed.widgets.find(w=>w.name==='pose3d_status').element.textContent.includes('PNG/JPEG/WebP'));
 const removed=new Node();removed.onNodeCreated();history=()=>new Promise(resolve=>complete=resolve);
 const finishing=sandbox.importImage(removed,file);await new Promise(setImmediate);removed.onRemoved();complete(goodHistory());await finishing;assert.equal(removed.changed,undefined);
 assert.equal(vm.runInContext("errorText({response:{error:{message:'Node is unavailable'}}})",sandbox),'Node is unavailable');
 assert.equal(listeners.size,0,'progress listeners cleaned after success, failure, stale import and removal');
 const drop=node.widgets.find(w=>w.name==='pose3d_import').element;let prevented=0;drop.ondragover({preventDefault:()=>prevented++,stopPropagation:()=>prevented++,dataTransfer:{}});assert.equal(prevented,2);
 console.log('Pose 3D UI: auto import, source camera, duplicate/stale/linked/error/removal, progress cleanup and drop checks passed');
}
run().catch(error=>{console.error(error);process.exitCode=1;});
