// SPDX-License-Identifier: GPL-3.0-only
import { app } from '../../scripts/app.js';
import { api } from '../../scripts/api.js';
import { maskState } from './mask_preview.js';
const states=new WeakMap();
const names=['pose_json','canvas_width','canvas_height','thickness','confidence'];
const val=(node,key)=>node.widgets?.find(w=>w.name===key)?.value;
const label=(en,ko,ja)=>{const lang=app.extensionManager?.setting?.get?.('Comfy.Locale')??'en';return lang.startsWith('ko')?ko:lang.startsWith('ja')?ja:en;};
const relevant=name=>names.includes(name)||name==='pose_keypoints';
const linked=node=>node.inputs?.some(i=>relevant(i.name)&&i.link!=null);
// Include the link itself: switching outputs on the same upstream node must
// invalidate its executed result just like changing an upstream widget.
const connectionKey=node=>JSON.stringify(node.inputs?.map((i,index)=>
    relevant(i.name)&&i.link!=null?[i.name,i.link,maskState(node.getInputNode?.(index))]:null));
const snapshot=node=>JSON.stringify([names.map(n=>val(node,n)),connectionKey(node)]);
const waiting=()=>label('Run once to preview connected pose inputs.','연결한 포즈는 한 번 실행하면 표시됩니다.','接続したポーズは一度実行すると表示されます。');
function accept(state,data){
    state.masks=data.masks.map(m=>({...m,data:Uint8Array.from(m.data)}));
    if(state.status)state.status.textContent=label('People: ','인물 수: ','人物数: ')+state.masks.length+' · '+label('Canvas overflow is clipped.','캔버스 밖은 잘라냅니다.','キャンバス外は切り取ります。');
}
export function poseSupports(node){
    const state=states.get(node);
    if(!state||state.key!==snapshot(node)){schedule(node);return {masks:[],unknown:true};}
    return {masks:state.masks??[],unknown:!state.masks,error:state.error};
}
export function rememberPosePreview(node,message){
    try{
        const info=JSON.parse(message?.text?.[0]);
        if(!info?.source)return;
        let state=states.get(node);if(!state){state={};states.set(node,state);}
        state.runtime={info,connections:connectionKey(node)};
        const data=message?.pose_masks?.[0];
        if(data){
            clearTimeout(state.timer);state.key=snapshot(node);state.error=null;accept(state,data);
            node.graph?.setDirtyCanvas(true,true);
        }else{state.key=null;schedule(node);}
    }catch{/* Missing execution preview. */}
}
function schedule(node){
    let state=states.get(node);if(!state){state={};states.set(node,state);}
    const key=snapshot(node);if(state.key===key)return;
    state.key=key;state.masks=null;state.error=null;clearTimeout(state.timer);
    if(state.runtime?.connections!==connectionKey(node))state.runtime=null;
    if(linked(node)&&!state.runtime){if(state.status)state.status.textContent=waiting();return;}
    const payload=Object.fromEntries(names.map(n=>[n,val(node,n)]));
    if(linked(node)){
        const info=state.runtime.info;
        for(const input of node.inputs??[]){
            if(input.link==null)continue;
            if(input.name==='pose_json'||input.name==='pose_keypoints')payload.pose_json=JSON.stringify(info.source);
            else if(input.name==='canvas_width'||input.name==='canvas_height')payload[input.name]=info.source[input.name];
            else if(input.name==='thickness'||input.name==='confidence')payload[input.name]=info[input.name];
        }
    }
    state.timer=setTimeout(async()=>{
        try{
            const response=await api.fetchApi('/rs_mc/pose_masks/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
            const data=await response.json();if(!response.ok)throw Error(data.error??'Pose preview failed.');
            if(states.get(node)!==state||state.key!==key||snapshot(node)!==key)return;
            accept(state,data);
        }catch(error){if(states.get(node)!==state||state.key!==key||snapshot(node)!==key)return;state.error=error.message;state.status&&(state.status.textContent=error.message);}
        node.graph?.setDirtyCanvas(true,true);
    },200);
}
app.registerExtension({name:'RS.MultiCharacter.PoseMasks',
    async beforeRegisterNodeDef(nodeType,nodeData){
        if(nodeData.name!=='RSMultiCharacterPoseMasks')return;
        const executed=nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted=function(message){const result=executed?.apply(this,arguments);rememberPosePreview(this,message);return result;};
        const configured=nodeType.prototype.onGraphConfigured;
        nodeType.prototype.onGraphConfigured=function(){const result=configured?.apply(this,arguments);schedule(this);return result;};
        const created=nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated=function(){
            const result=created?.apply(this,arguments);
            const upload=document.createElement('input');upload.type='file';upload.accept='.json,application/json';upload.style.display='none';
            const status=document.createElement('div');status.style.cssText='color:#ccd5df;padding:6px;white-space:pre-wrap;font-size:12px';
            const state={status};states.set(this,state);
            this.addDOMWidget('pose_status','RS_POSE_STATUS',status,{serialize:false,hideOnZoom:false});
            const button=this.addWidget('button',label('Load OpenPose JSON','OpenPose JSON 불러오기','OpenPose JSONを開く'),null,()=>upload.click(),{serialize:false});button.serialize=false;
            upload.onchange=async()=>{const f=upload.files?.[0];if(!f)return;try{if(f.size>2*1024*1024)throw Error('JSON must be under 2 MiB.');const raw=await f.text();JSON.parse(raw);const widget=this.widgets.find(w=>w.name==='pose_json');widget.value=raw;widget.callback?.(raw);this.graph?.change?.();schedule(this);}catch(e){status.textContent=e.message;}finally{upload.value='';}};
            this._rsPoseUpload=upload;
            for(const widget of this.widgets??[])if(names.includes(widget.name)){const old=widget.callback;widget.callback=function(){const r=old?.apply(this,arguments);schedule(node);return r;};}
            const node=this;schedule(this);return result;
        };
        const removed=nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved=function(){clearTimeout(states.get(this)?.timer);states.delete(this);return removed?.apply(this,arguments);};
    }
});
