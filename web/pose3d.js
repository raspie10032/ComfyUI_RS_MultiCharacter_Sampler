// SPDX-License-Identifier: GPL-3.0-only
import {app} from '../../scripts/app.js';
import {api} from '../../scripts/api.js';
import {chineseLocale,chineseText} from './i18n.js';
const states=new WeakMap();
const widget=node=>node.widgets?.find(w=>w.name==='scene_json');
const linked=node=>node.inputs?.some(i=>i.name==='scene_json'&&i.link!=null);
const key=node=>JSON.stringify([widget(node)?.value,node.inputs?.find(i=>i.name==='scene_json')?.link]);
const locale=()=>app.extensionManager?.setting?.get?.('Comfy.Locale')??'en';
const label=(en,ko,ja)=>chineseLocale(locale())?chineseText(en,locale()):locale().startsWith('ko')?ko:locale().startsWith('ja')?ja:en;
const errorText=error=>error?.message??error?.response?.error?.message??'Image → 3D failed.';
async function estimateImagePose(file,requestId,signal,onProgress=()=>{}){
    const types={'image/png':'png','image/jpeg':'jpg','image/webp':'webp'};
    if(!(file instanceof Blob)||!types[file.type]||file.size>20*1024*1024)throw Error('Choose a PNG/JPEG/WebP under 20 MB.');
    onProgress(label('Uploading image…','이미지를 읽는 중…','画像を読み込み中…'));
    const form=new FormData();form.append('image',file,`rs-pose-${requestId}.${types[file.type]}`);form.append('type','input');form.append('subfolder','RS_PoseImports');
    const uploaded=await api.fetchApi('/upload/image',{method:'POST',body:form,signal});
    if(!uploaded.ok)throw Error(`Image upload failed (HTTP ${uploaded.status}).`);
    const image=await uploaded.json(),load='rs_pose_load_'+requestId,estimate='rs_pose_estimate_'+requestId;
    signal.throwIfAborted();
    const progress=event=>{if(String(event.detail?.node)===estimate)onProgress(event.detail.text);};
    api.addEventListener('rs_mc_tagger_progress',progress);
    try{
    onProgress(label('Waiting in ComfyUI queue. First use downloads SAM 3D Body (2.83 GB).','ComfyUI 대기열에서 순서를 기다립니다. 최초 사용 시 SAM 3D Body(2.83GB)를 받습니다.','ComfyUIのキューで待機中。初回はSAM 3D Body（2.83GB）を取得します。'));
    const queued=await api.queuePrompt(-1,{output:{
        [load]:{class_type:'LoadImage',inputs:{image:[image.subfolder,image.name].filter(Boolean).join('/')}},
        [estimate]:{class_type:'RSImageToPose3D',inputs:{image:[load,0],character_number:1,base_scene:''}},
    },workflow:{}});
    if(!queued.prompt_id)throw Error(queued.error?.message??'Image → 3D prompt was not accepted.');
    while(!signal.aborted){
        const response=await api.fetchApi('/history/'+encodeURIComponent(queued.prompt_id),{signal});
        if(!response.ok)throw Error(`Cannot read pose result (HTTP ${response.status}).`);
        const entry=(await response.json())[queued.prompt_id];
        if(entry){
            const output=entry.outputs?.[estimate]?.rs_pose_image?.[0];if(output?.pose&&output?.scene)return output;
            const messages=entry.status?.messages??[];
            const failure=messages.find(([name])=>name==='execution_error'||name==='execution_interrupted');
            if(failure)throw Error(failure[1].exception_message??'Image → 3D was interrupted.');
            if(entry.status?.completed)throw Error('Image → 3D finished without an editable pose.');
        }
        await new Promise(resolve=>{
            const done=()=>{clearTimeout(timer);signal.removeEventListener('abort',done);resolve();};
            const timer=setTimeout(done,1000);signal.addEventListener('abort',done,{once:true});
        });
    }
    throw new DOMException('Editor closed.','AbortError');
    }finally{api.removeEventListener('rs_mc_tagger_progress',progress);}
}
function saveScene(node,scene){
    const raw=JSON.stringify(scene);if(raw.length>100000)throw Error('Scene must be under 100 KB.');
    widget(node).value=raw;widget(node).callback?.(raw);node.graph?.change?.();states.get(node).key=null;schedule(node);
}
async function importImage(node,file){
    const s=states.get(node);if(!s||s.importing)return;
    if(linked(node)){s.status.textContent=label('Import at the connected scene source.','연결된 장면의 원본 노드에 이미지를 넣어 주세요.','接続元のノードに画像を入れてください。');return;}
    const before=key(node),controller=new AbortController();s.importController=controller;s.importing=true;s.upload.disabled=true;
    try{
        const result=await estimateImagePose(file,crypto.randomUUID(),controller.signal,message=>{s.status.textContent=message;});
        if(states.get(node)!==s||controller.signal.aborted)return;
        if(key(node)!==before)throw Error(label('Scene changed while estimating. Import again.','추정 중 장면이 바뀌었습니다. 이미지를 다시 넣어 주세요.','推定中にシーンが変更されました。もう一度画像を入れてください。'));
        saveScene(node,result.scene);s.importing=false;openEditor(node);
    }catch(error){if(!controller.signal.aborted)s.status.textContent=errorText(error);}
    finally{if(states.get(node)===s){s.importing=false;s.upload.disabled=false;}}
}
function accept(node,data){
    const s=states.get(node);if(!s)return;
    s.masks=data.masks.map(m=>({...m,data:Uint8Array.from(m.data)}));s.key=key(node);s.error=null;
    const c=s.canvas,ctx=c.getContext('2d');c.height=Math.round(c.width*data.canvas_height/data.canvas_width);
    ctx.fillStyle='#171c25';ctx.fillRect(0,0,c.width,c.height);
    for(const m of s.masks){
        ctx.fillStyle=['#ff8d9188','#81bcff88','#94dd9d88','#ffd27f88','#c3a0ff88'][(m.number-1)%5];
        for(let y=0;y<m.height;y++)for(let x=0;x<m.width;x++)if(m.data[y*m.width+x])ctx.fillRect(x*c.width/m.width,y*c.height/m.height,Math.ceil(c.width/m.width),Math.ceil(c.height/m.height));
        ctx.fillStyle='white';ctx.font='bold 16px sans-serif';ctx.fillText(String(m.number),m.center[0]*c.width,m.center[1]*c.height);
    }
    s.status.textContent=label('Character slots: ','캐릭터 번호: ','人物番号: ')+s.masks.map(m=>m.number).join(', ');
    node.graph?.setDirtyCanvas(true,true);
}
function schedule(node){
    const s=states.get(node);if(!s)return;const snapshot=key(node);if(s.key===snapshot)return;
    s.key=snapshot;s.masks=null;s.error=null;clearTimeout(s.timer);s.controller?.abort();
    s.canvas.getContext('2d').clearRect(0,0,s.canvas.width,s.canvas.height);
    if(linked(node)){s.status.textContent=label('Run once to preview the connected scene.','연결한 장면은 한 번 실행하면 표시됩니다.','接続シーンは一度実行すると表示されます。');return;}
    s.timer=setTimeout(async()=>{
        const controller=new AbortController();s.controller=controller;
        try{
            const response=await api.fetchApi('/rs_mc/pose3d/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:widget(node).value,signal:controller.signal});
            const data=await response.json();if(!response.ok)throw Error(data.error??'3D mask preview failed.');
            if(states.get(node)!==s||key(node)!==snapshot)return;accept(node,data);
        }catch(error){if(controller.signal.aborted||states.get(node)!==s||key(node)!==snapshot)return;s.error=error.message;s.status.textContent=error.message;}
    },180);
}
export function pose3dSupports(node){
    const s=states.get(node);if(!s||s.key!==key(node)){schedule(node);return {masks:[],unknown:true};}
    return {masks:s.masks??[],unknown:!s.masks,error:s.error};
}
function openEditor(node){
    const s=states.get(node);if(!s)return;
    if(s.importing)return;
    if(linked(node)){s.status.textContent=label('Edit the connected scene at its source.','연결된 장면은 원본 노드에서 수정해 주세요.','接続元でシーンを編集してください。');return;}
    let scene;try{scene=JSON.parse(widget(node).value);}catch{s.status.textContent='Invalid scene JSON.';return;}
    if(s.close){s.frame.focus();return;}
    const overlay=document.createElement('div');overlay.className='rs-pose3d-modal';overlay.setAttribute('role','dialog');overlay.setAttribute('aria-label','RS 3D Pose Masks');overlay.setAttribute('aria-modal','true');overlay.style.cssText='position:fixed;inset:0;z-index:10000;background:#000b;display:flex;align-items:center;justify-content:center;';
    const panel=document.createElement('div');panel.style.cssText='position:relative;width:96vw;height:92vh;border:1px solid #52657a;background:#161b23;';
    const frame=document.createElement('iframe'),token=crypto.randomUUID();s.frame=frame;
    frame.src=new URL('./pose3d/index.html#'+token,import.meta.url).href;frame.title='RS 3D Pose Masks';frame.style.cssText='width:100%;height:100%;border:0';
    const close=document.createElement('button');close.textContent='×';close.title=label('Close editor','편집기 닫기','エディターを閉じる');close.style.cssText='position:absolute;right:5px;top:5px;z-index:1;font-size:23px;color:white;background:#273648;border:1px solid #60748e;cursor:pointer;';
    const imageController=new AbortController();let imageBusy=false;
    const receive=async event=>{
        if(event.source!==frame.contentWindow||event.origin!==location.origin||event.data?.token!==token)return;
        if(event.data.type==='rs-pose3d-ready')frame.contentWindow.postMessage({type:'rs-pose3d-init',scene,locale:locale(),token},location.origin);
        if(event.data.type==='rs-pose3d-apply'){
            saveScene(node,event.data.scene);
        }
        if(event.data.type==='rs-pose3d-image-request'&&!imageBusy){
            const requestId=event.data.requestId;
            if(typeof requestId!=='string'||!/^[-a-z0-9]{36}$/i.test(requestId))return;
            imageBusy=true;
            try{
                const result=await estimateImagePose(event.data.file,requestId,imageController.signal,message=>{
                    if(!imageController.signal.aborted)frame.contentWindow.postMessage({type:'rs-pose3d-image-progress',message,requestId,token},location.origin);
                });
                if(!imageController.signal.aborted)frame.contentWindow.postMessage({type:'rs-pose3d-image-result',...result,requestId,token},location.origin);
            }catch(error){if(!imageController.signal.aborted)frame.contentWindow.postMessage({type:'rs-pose3d-image-error',error:errorText(error),requestId,token},location.origin);}
            finally{imageBusy=false;}
        }
    };
    window.addEventListener('message',receive);
    s.close=()=>{imageController.abort();window.removeEventListener('message',receive);overlay.remove();s.close=null;s.frame=null;};
    close.onclick=s.close;overlay.append(panel);panel.append(frame,close);document.body.append(overlay);
}
app.registerExtension({name:'RS.MultiCharacter.Pose3D',
    async beforeRegisterNodeDef(nodeType,nodeData){
        if(nodeData.name!=='RSMultiCharacterPose3D')return;
        const created=nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated=function(){
            const result=created?.apply(this,arguments),node=this;
            const canvas=document.createElement('canvas');canvas.width=240;canvas.height=320;canvas.style.cssText='max-width:100%;max-height:320px;display:block;margin:auto;background:#171c25';
            const status=document.createElement('div');status.style.cssText='padding:6px;white-space:pre-wrap;color:#c9d6e3;font-size:12px';states.set(this,{canvas,status});
            const scene=widget(this);scene.hidden=true;scene.type='rs-mc-hidden';scene.computeSize=()=>[0,-4];
            const old=scene.callback;scene.callback=function(){const r=old?.apply(this,arguments);schedule(node);return r;};
            this.addWidget('button',label('Open 3D editor','3D 편집기 열기','3Dエディターを開く'),null,()=>openEditor(this),{serialize:false}).serialize=false;
            const drop=document.createElement('div');drop.style.cssText='padding:8px;border:1px dashed #70879e;border-radius:5px;text-align:center;color:#dce7f2;background:#202833';
            const upload=document.createElement('button');upload.textContent=label('Image → 3D','이미지 → 3D','画像 → 3D');upload.style.cssText='width:100%;padding:8px;cursor:pointer';states.get(this).upload=upload;
            const input=document.createElement('input');input.type='file';input.accept='image/png,image/jpeg,image/webp';input.hidden=true;
            const help=document.createElement('p');help.textContent=label('Drop one person’s image here. Replaces this scene and opens 3D automatically.','한 명이 나온 이미지를 놓으세요. 현재 장면을 교체하고 3D를 바로 엽니다.','1人の画像をドロップ。現在のシーンを置き換えて3Dを開きます。');help.style.cssText='font-size:11px;margin:6px 0';
            upload.onclick=()=>{if(!states.get(node)?.importing)input.click();};input.onchange=()=>{const file=input.files[0];input.value='';if(file)importImage(node,file);};
            drop.ondragover=event=>{event.preventDefault();event.stopPropagation();event.dataTransfer.dropEffect='copy';};
            drop.ondrop=event=>{event.preventDefault();event.stopPropagation();if(event.dataTransfer.files[0])importImage(node,event.dataTransfer.files[0]);};drop.append(upload,input,help);
            const importer=this.addDOMWidget('pose3d_import','RS_POSE3D_IMPORT',drop,{serialize:false,hideOnZoom:false});importer.serialize=false;importer.computeSize=()=>[240,100];
            const preview=this.addDOMWidget('pose3d_preview','RS_POSE3D_PREVIEW',canvas,{serialize:false,hideOnZoom:false});preview.serialize=false;preview.computeSize=()=>[240,330];
            const notice=this.addDOMWidget('pose3d_status','RS_POSE3D_STATUS',status,{serialize:false,hideOnZoom:false});notice.serialize=false;notice.computeSize=()=>[240,65];schedule(this);return result;
        };
        const configure=nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure=function(data){
            const result=configure?.apply(this,arguments);
            // Old scenes were mask-only; never silently add a trained adapter
            // to a workflow that may already have native MODEL patches.
            const values=data?.widgets_values_named;
            if (!(values && 'pose_control' in values) && (!Array.isArray(data?.widgets_values) || data.widgets_values.length < 5)) {
                const mode=this.widgets?.find(w=>w.name==='pose_control');if(mode)mode.value='masks_only';
            }
            return result;
        };
        const configured=nodeType.prototype.onGraphConfigured;
        nodeType.prototype.onGraphConfigured=function(){const r=configured?.apply(this,arguments);schedule(this);return r;};
        const executed=nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted=function(message){const r=executed?.apply(this,arguments);if(message?.pose3d?.[0])accept(this,message.pose3d[0]);return r;};
        const removed=nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved=function(){const s=states.get(this);clearTimeout(s?.timer);s?.controller?.abort();s?.importController?.abort();s?.close?.();states.delete(this);return removed?.apply(this,arguments);};
    }
});
