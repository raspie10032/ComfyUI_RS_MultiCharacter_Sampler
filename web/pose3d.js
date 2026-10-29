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
    if(linked(node)){s.status.textContent=label('Edit the connected scene at its source.','연결된 장면은 원본 노드에서 수정해 주세요.','接続元でシーンを編集してください。');return;}
    let scene;try{scene=JSON.parse(widget(node).value);}catch{s.status.textContent='Invalid scene JSON.';return;}
    if(s.close){s.frame.focus();return;}
    const overlay=document.createElement('div');overlay.className='rs-pose3d-modal';overlay.setAttribute('role','dialog');overlay.setAttribute('aria-label','RS 3D Pose Masks');overlay.setAttribute('aria-modal','true');overlay.style.cssText='position:fixed;inset:0;z-index:10000;background:#000b;display:flex;align-items:center;justify-content:center;';
    const panel=document.createElement('div');panel.style.cssText='position:relative;width:96vw;height:92vh;border:1px solid #52657a;background:#161b23;';
    const frame=document.createElement('iframe'),token=crypto.randomUUID();s.frame=frame;
    frame.src=new URL('./pose3d/index.html#'+token,import.meta.url).href;frame.title='RS 3D Pose Masks';frame.style.cssText='width:100%;height:100%;border:0';
    const close=document.createElement('button');close.textContent='×';close.title=label('Close editor','편집기 닫기','エディターを閉じる');close.style.cssText='position:absolute;right:5px;top:5px;z-index:1;font-size:23px;color:white;background:#273648;border:1px solid #60748e;cursor:pointer;';
    const receive=event=>{
        if(event.source!==frame.contentWindow||event.origin!==location.origin||event.data?.token!==token)return;
        if(event.data.type==='rs-pose3d-ready')frame.contentWindow.postMessage({type:'rs-pose3d-init',scene,locale:locale(),token},location.origin);
        if(event.data.type==='rs-pose3d-apply'){
            const raw=JSON.stringify(event.data.scene);if(raw.length>100000)return;
            widget(node).value=raw;widget(node).callback?.(raw);node.graph?.change?.();s.key=null;schedule(node);
        }
    };
    window.addEventListener('message',receive);
    s.close=()=>{window.removeEventListener('message',receive);overlay.remove();s.close=null;s.frame=null;};
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
            const preview=this.addDOMWidget('pose3d_preview','RS_POSE3D_PREVIEW',canvas,{serialize:false,hideOnZoom:false});preview.serialize=false;preview.computeSize=()=>[240,330];
            const notice=this.addDOMWidget('pose3d_status','RS_POSE3D_STATUS',status,{serialize:false,hideOnZoom:false});notice.serialize=false;notice.computeSize=()=>[240,65];schedule(this);return result;
        };
        const configured=nodeType.prototype.onGraphConfigured;
        nodeType.prototype.onGraphConfigured=function(){const r=configured?.apply(this,arguments);schedule(this);return r;};
        const executed=nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted=function(message){const r=executed?.apply(this,arguments);if(message?.pose3d?.[0])accept(this,message.pose3d[0]);return r;};
        const removed=nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved=function(){const s=states.get(this);clearTimeout(s?.timer);s?.controller?.abort();s?.close?.();states.delete(this);return removed?.apply(this,arguments);};
    }
});
