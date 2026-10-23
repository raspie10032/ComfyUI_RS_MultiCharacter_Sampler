// SPDX-License-Identifier: GPL-3.0-only
import { chineseLocale, chineseText } from "./i18n.js";
import { app } from '../../scripts/app.js';
import { api } from '../../scripts/api.js';
import { maskState } from './mask_preview.js';
const states=new WeakMap();
const names=['pose_json','canvas_width','canvas_height','thickness','confidence','pose_image'];
const val=(node,key)=>node.widgets?.find(w=>w.name===key)?.value;
const label=(en,ko,ja)=>{const lang=app.extensionManager?.setting?.get?.('Comfy.Locale')??'en';return chineseLocale(lang)?chineseText(en,lang):lang.startsWith('ko')?ko:lang.startsWith('ja')?ja:en;};
const relevant=name=>names.includes(name)||name==='pose_keypoints'||name==='image';
const linked=node=>node.inputs?.some(i=>relevant(i.name)&&i.link!=null);
// Include the link itself: switching outputs on the same upstream node must
// invalidate its executed result just like changing an upstream widget.
const connectionKey=node=>JSON.stringify(node.inputs?.map((i,index)=>
    relevant(i.name)&&i.link!=null?[i.name,i.link,maskState(node.getInputNode?.(index))]:null));
const snapshot=node=>JSON.stringify([names.map(n=>val(node,n)),connectionKey(node)]);
const waiting=()=>label('Run once to preview connected pose inputs.','연결한 포즈는 한 번 실행하면 표시됩니다.','接続したポーズは一度実行すると表示されます。');
function accept(state,data){
    state.masks=data.masks.map(m=>({...m,data:Uint8Array.from(m.data)}));
    if(state.canvas&&data.canvas_width&&data.canvas_height)state.canvas.height=Math.round(state.canvas.width*data.canvas_height/data.canvas_width);
    if(state.status){
        state.status.textContent=label('People: ','인물 수: ','人物数: ')+state.masks.length+' · '+
            (['png','connected_image'].includes(data.source_kind)?label('PNG · numbered left to right. Check overlapping joints.','PNG · 왼쪽부터 번호 지정. 겹친 관절을 확인하세요.','PNG · 左から番号順。重なる関節を確認してください。'):
            label('Canvas overflow is clipped.','캔버스 밖은 잘라냅니다.','キャンバス外は切り取ります。'));
    }
    paint(state);
}
function paint(state){
    const ctx=state.canvas?.getContext?.('2d');if(!ctx)return;
    const canvas=state.canvas;ctx.fillStyle='#171c25';ctx.fillRect(0,0,canvas.width,canvas.height);
    for(const [i,m] of (state.masks??[]).entries()){
        ctx.fillStyle=['#ff8d9166','#81bcff66','#94dd9d66','#ffd27f66','#c3a0ff66'][i%5];
        for(let y=0;y<m.height;y++)for(let x=0;x<m.width;x++)if(m.data[y*m.width+x])
            ctx.fillRect(x*canvas.width/m.width,y*canvas.height/m.height,Math.ceil(canvas.width/m.width),Math.ceil(canvas.height/m.height));
        ctx.fillStyle='white';ctx.font='bold 16px sans-serif';ctx.fillText(String(i+1),m.center[0]*canvas.width,m.center[1]*canvas.height);
    }
    if(state.sourceImage){ctx.globalCompositeOperation='screen';ctx.drawImage(state.sourceImage,0,0,canvas.width,canvas.height);ctx.globalCompositeOperation='source-over';}
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
    paint(state);
    if(state.runtime?.connections!==connectionKey(node))state.runtime=null;
    if(linked(node)&&!state.runtime){if(state.status)state.status.textContent=waiting();return;}
    if(!linked(node)&&(!val(node,'pose_image')||val(node,'pose_image')==='(none)')&&['','{"people":[]}'].includes(val(node,'pose_json')??'')){
        if(state.status)state.status.textContent=label('Load or drop a colored pose PNG to create masks.','컬러 뼈대 PNG를 불러오거나 여기에 끌어다 놓으세요.','カラーポーズPNGを開くか、ここにドロップしてください。');
        return;
    }
    const payload=Object.fromEntries(names.map(n=>[n,val(node,n)]));
    if(linked(node)){
        const info=state.runtime.info;
        for(const input of node.inputs??[]){
            if(input.link==null)continue;
            if(['pose_json','pose_keypoints','image','pose_image'].includes(input.name)){
                payload.pose_json=JSON.stringify(info.source);payload.pose_image='(none)';
            }
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
        nodeType.prototype.onGraphConfigured=function(){const result=configured?.apply(this,arguments);states.get(this)?.showSource?.();schedule(this);return result;};
        const created=nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated=function(){
            const result=created?.apply(this,arguments);
            const upload=document.createElement('input');upload.type='file';upload.accept='.json,application/json';upload.style.display='none';
            const png=document.createElement('input');png.type='file';png.accept='.png,.webp,.jpg,.jpeg,image/png,image/webp,image/jpeg';png.style.display='none';
            const status=document.createElement('div');status.style.cssText='color:#ccd5df;padding:6px;white-space:pre-wrap;font-size:12px';
            const state={status};states.set(this,state);
            const statusWidget=this.addDOMWidget('pose_status','RS_POSE_STATUS',status,{serialize:false,hideOnZoom:false});
            statusWidget.computeSize=()=>[240,54];
            const canvas=document.createElement('canvas');canvas.width=240;canvas.height=300;canvas.style.cssText='display:block;max-width:100%;max-height:300px;margin:auto;background:#171c25';state.canvas=canvas;
            const previewWidget=this.addDOMWidget('pose_mask_preview','RS_POSE_PREVIEW',canvas,{serialize:false,hideOnZoom:false});
            previewWidget.computeSize=()=>[240,310];
            const addButton=(name,callback)=>{const b=this.addWidget('button',name,null,callback,{serialize:false});b.serialize=false;return b;};
            addButton(label('Load Pose PNG','뼈대 PNG 불러오기','ポーズPNGを開く'),()=>png.click());
            const showSource=()=>{
                state.sourceImage=null;const file=val(this,'pose_image');
                if(file&&file!=='(none)'&&typeof Image!=='undefined'){
                    const img=new Image();img.onload=()=>{if(states.get(this)!==state||val(this,'pose_image')!==file)return;
                        state.sourceImage=img;canvas.height=Math.round(canvas.width*img.naturalHeight/img.naturalWidth);paint(state);};
                    const slash=file.lastIndexOf('/');
                    img.src=api.apiURL('/view?'+new URLSearchParams({filename:file.slice(slash+1),subfolder:slash>=0?file.slice(0,slash):'',type:'input'}));
                }
            };
            state.showSource=showSource;
            const receiveImage=async f=>{
                const revision=state.uploadRevision=(state.uploadRevision??0)+1;
                status.textContent=label('Reading pose PNG…','뼈대 PNG를 읽는 중…','ポーズPNGを読込中…');
                try{
                    const form=new FormData();form.append('image',f);form.append('subfolder','RS_OpenPose');form.append('type','input');
                    const response=await api.fetchApi('/upload/image',{method:'POST',body:form});
                    const data=await response.json();if(!response.ok)throw Error(data.error??`HTTP ${response.status}`);
                    if(states.get(this)!==state||revision!==state.uploadRevision)return;
                    const widget=this.widgets.find(w=>w.name==='pose_image');
                    const file=[data.subfolder,data.name].filter(Boolean).join('/');
                    if(!widget.options.values.includes(file))widget.options.values.push(file);
                    widget.value=file;widget.callback?.(file);this.graph?.change?.();schedule(this);
                }catch(e){if(states.get(this)===state&&revision===state.uploadRevision)status.textContent=e.message;}
            };
            png.onchange=async()=>{const f=png.files?.[0];if(f)await receiveImage(f);png.value='';};
            this._rsPoseImageUpload=png;
            const oldDrop=this.onDragDrop,oldOver=this.onDragOver;
            const imageFile=event=>Array.from(event?.dataTransfer?.files??[]).find(f=>/image\/(png|jpeg|webp)/.test(f.type));
            this.onDragOver=function(event){return imageFile(event)?true:oldOver?.apply(this,arguments);};
            this.onDragDrop=function(event){const f=imageFile(event);if(f){event.preventDefault?.();void receiveImage(f);return true;}return oldDrop?.apply(this,arguments);};
            for(const el of [status,canvas]){
                el.ondragover=event=>{event.preventDefault();event.stopPropagation();};
                el.ondrop=event=>{event.preventDefault();event.stopPropagation();const f=imageFile(event);if(f)void receiveImage(f);};
            }
            addButton(label('Load JSON (advanced)','JSON 불러오기 (고급)','JSONを開く（詳細）'),()=>upload.click());
            upload.onchange=async()=>{const f=upload.files?.[0];if(!f)return;try{if(f.size>2*1024*1024)throw Error('JSON must be under 2 MiB.');const raw=await f.text();JSON.parse(raw);const image=this.widgets.find(w=>w.name==='pose_image');if(image){image.value='(none)';image.callback?.('(none)');}const widget=this.widgets.find(w=>w.name==='pose_json');widget.value=raw;widget.callback?.(raw);this.graph?.change?.();schedule(this);}catch(e){status.textContent=e.message;}finally{upload.value='';}};
            const json=this.widgets.find(w=>w.name==='pose_json');
            const original={type:json.type,computeSize:json.computeSize,hidden:json.hidden};
            let showJson=false;
            const toggle=()=>{json.type=showJson?original.type:'rs-mc-hidden';json.hidden=showJson?original.hidden:true;json.computeSize=showJson?original.computeSize:()=>[0,-4];this.setSize?.(this.computeSize());};
            toggle();addButton(label('Show / hide JSON','JSON 펼치기 / 접기','JSONを表示・非表示'),()=>{showJson=!showJson;toggle();});
            this._rsPoseUpload=upload;
            for(const widget of this.widgets??[])if(names.includes(widget.name)){const old=widget.callback;widget.callback=function(){const r=old?.apply(this,arguments);if(widget.name==='pose_image')showSource();schedule(node);return r;};}
            const node=this;showSource();schedule(this);return result;
        };
        const removed=nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved=function(){clearTimeout(states.get(this)?.timer);states.delete(this);return removed?.apply(this,arguments);};
    }
});
