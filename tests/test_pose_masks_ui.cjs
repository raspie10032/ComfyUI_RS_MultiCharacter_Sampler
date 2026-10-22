const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
let extension,nextTimer=0,locale='en',pending=null;
const timers=new Map(),calls=[];
const raster={masks:[{width:2,height:2,data:[1,0,1,0],center:[.25,.5]}]};
class UploadForm {constructor(){this.fields={};}append(k,v){this.fields[k]=v;}}
const imageURLs=[];
const sandbox={
 FormData:UploadForm,URLSearchParams,
 Image:class{set src(value){imageURLs.push(value);this.naturalWidth=512;this.naturalHeight=768;this.onload?.();}},
 app:{registerExtension(e){extension=e;},extensionManager:{setting:{get:()=>locale}}},
 api:{apiURL:path=>path,async fetchApi(url,options){
  if(url==='/upload/image'){calls.push({url,payload:options.body.fields});return {ok:true,json:async()=>({subfolder:'RS_OpenPose',name:options.body.fields.image.name})};}
  calls.push({url,payload:JSON.parse(options.body)});return pending?await pending:{ok:true,json:async()=>raster};}},
 document:{createElement(){return {style:{},click(){}};}},
 setTimeout(callback){const id=++nextTimer;timers.set(id,callback);return id;},clearTimeout(id){timers.delete(id);},
};
const load=file=>fs.readFileSync(file,'utf8').replace(/^import[^\n]*\n/gm,'').replaceAll('export function','function');
const maskSandbox={app:{},api:{},URLSearchParams};vm.runInNewContext(load('web/mask_preview.js'),maskSandbox);
sandbox.maskState=maskSandbox.maskState;vm.runInNewContext(load('web/pose_masks.js'),sandbox);
const {poseSupports}=sandbox;
class Node{
 constructor(){this.type='RSMultiCharacterPoseMasks';this.inputs=[];
  this.widgets=Object.entries({pose_json:'original',thickness:1,confidence:.2,canvas_width:512,canvas_height:768,pose_image:'(none)'}).map(([name,value])=>({name,value,options:{values:['(none)']}}));
  this.graph={setDirtyCanvas(){}};}
 addDOMWidget(name,type,element,options){if(name==='pose_status')this.status=element;const widget={name,type,element,...options};this.widgets.push(widget);return widget;}
 addWidget(type,name,value,callback,options){const widget={type,name,value,callback,...options};this.widgets.push(widget);return widget;}
 onExecuted(){this.previousExecuted=true;}onGraphConfigured(){this.previousConfigured=true;}onRemoved(){this.previousRemoved=true;}
}
const widget=(node,name)=>node.widgets.find(w=>w.name===name);
async function flush(){const callbacks=[...timers.values()];timers.clear();for(const callback of callbacks)await callback();}
function message(){return {text:[JSON.stringify({source:{people:[{}],canvas_width:512,canvas_height:768},thickness:1.4,confidence:.3})],pose_masks:[raster]};}
(async()=>{
 await extension.beforeRegisterNodeDef(Node,{name:'RSMultiCharacterPoseMasks'});
 const direct=new Node();direct.onNodeCreated();await flush();
 assert.equal(widget(direct,'pose_json').hidden,true);
 assert.deepEqual(Array.from(widget(direct,'pose_mask_preview').computeSize()),[240,310]);
 assert.equal(poseSupports(direct).unknown,false);assert.deepEqual(Array.from(poseSupports(direct).masks[0].data),[1,0,1,0]);
 assert.equal(calls.at(-1).payload.pose_json,'original');assert.equal(direct.widgets.find(w=>w.name==='pose_status').serialize,false);
 assert.equal(direct.widgets.at(-1).serialize,false);
 widget(direct,'thickness').value=2;widget(direct,'thickness').callback();await flush();assert.equal(calls.at(-1).payload.thickness,2);
 const upstream={id:7,type:'PoseProvider',widgets:[{name:'image',value:'first.png'}],inputs:[]};
 const connected=new Node();connected.inputs=[{name:'pose_keypoints',link:21}];connected.getInputNode=()=>upstream;
 connected.onNodeCreated();await flush();assert.equal(poseSupports(connected).unknown,true);assert.match(connected.status.textContent,/Run once/);
 const before=calls.length;connected.onExecuted(message());assert.equal(connected.previousExecuted,true);
 assert.equal(poseSupports(connected).unknown,false);assert.equal(calls.length,before); // No second compile for an executed mask.
 widget(connected,'thickness').value=1.8;widget(connected,'thickness').callback();await flush();
 assert.equal(poseSupports(connected).unknown,false);assert.equal(calls.at(-1).payload.thickness,1.8);
 assert.deepEqual(JSON.parse(calls.at(-1).payload.pose_json),JSON.parse(message().text[0]).source);
 // A changed provider or a different output link cannot keep the previous mask.
 upstream.widgets[0].value='second.png';assert.equal(poseSupports(connected).unknown,true);await flush();
 assert.equal(calls.length,before+1);assert.match(connected.status.textContent,/Run once/);
 connected.onExecuted(message());assert.equal(poseSupports(connected).unknown,false);
 connected.inputs[0].link=22;assert.equal(poseSupports(connected).unknown,true);
 connected.onExecuted(message());assert.equal(poseSupports(connected).unknown,false);
 // Connected controls use executed values; unconnected JSON stays editable.
 const scalar=new Node();scalar.inputs=[{name:'thickness',link:23}];scalar.getInputNode=()=>upstream;
 scalar.onNodeCreated();scalar.onExecuted(message());widget(scalar,'pose_json').value='edited JSON';widget(scalar,'pose_json').callback();await flush();
 assert.equal(calls.at(-1).payload.pose_json,'edited JSON');assert.equal(calls.at(-1).payload.thickness,1.4);
 scalar.inputs=[];scalar.onGraphConfigured();await flush();assert.equal(scalar.previousConfigured,true);assert.equal(calls.at(-1).payload.thickness,1);
 // Stale HTTP responses never revive old masks after an edit.
 let resolve;pending=new Promise(done=>resolve=done);widget(direct,'pose_json').value='queued';direct.onGraphConfigured();
 const inflight=flush();widget(direct,'pose_json').value='newer';resolve({ok:true,json:async()=>raster});await inflight;pending=null;
 assert.equal(poseSupports(direct).unknown,true);await flush();assert.equal(poseSupports(direct).unknown,false);
 pending=Promise.resolve({ok:false,json:async()=>({error:'Invalid pose'})});
 widget(direct,'pose_json').value='bad';widget(direct,'pose_json').callback();await flush();pending=null;
 assert.equal(poseSupports(direct).unknown,true);assert.equal(poseSupports(direct).error,'Invalid pose');direct.onRemoved();assert.equal(direct.previousRemoved,true);
 const png=new Node();png.onNodeCreated();await flush();
 png._rsPoseImageUpload.files=[{name:'two-people.png'}];await png._rsPoseImageUpload.onchange();await flush();
 assert.equal(widget(png,'pose_image').value,'RS_OpenPose/two-people.png');
 assert.equal(calls.at(-1).payload.pose_image,'RS_OpenPose/two-people.png');
 assert(imageURLs.at(-1).includes('filename=two-people.png'));assert(imageURLs.at(-1).includes('subfolder=RS_OpenPose'));
 assert.equal(png._rsPoseImageUpload.value,'');
 png.onDragDrop({dataTransfer:{files:[{name:'dropped.png',type:'image/png'}]},preventDefault(){}});
 await new Promise(resolve=>setImmediate(resolve));await flush();
 assert.equal(widget(png,'pose_image').value,'RS_OpenPose/dropped.png');
 assert.equal(widget(png,'pose_json').value,'original');
 const blank=new Node();widget(blank,'pose_json').value='';blank.onNodeCreated();await flush();assert(blank.status.textContent.includes('pose PNG'));
 for(const [language,expected] of [['ko','한 번 실행'],['ja','一度実行']]){locale=language;const node=new Node();node.inputs=[{name:'pose_keypoints',link:30}];node.onNodeCreated();assert.ok(node.status.textContent.includes(expected));node.onRemoved();}
 console.log('Pose previews: direct/connected inputs, executed rasters, local edits, upstream/link invalidation, restoration, stale requests and localized status passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
