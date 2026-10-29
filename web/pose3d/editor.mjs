// SPDX-License-Identifier: GPL-3.0-only
import * as T from 'three';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {TransformControls} from 'three/examples/jsm/controls/TransformControls.js';
import {JOINTS,defaultScene,mannequin as legacyMannequin,skeleton as legacySkeleton,rotation,mv,sub,mm} from './model.mjs';
import {initRig,rigControls,defaultRigScene,defaultPerson,preset,rigMannequin,rigSkeleton} from './mhr.mjs';
try {
    const response=await fetch(new URL('./mhr-body.json.gz',import.meta.url));
    if(!response.ok)throw Error(`MHR asset HTTP ${response.status}`);
    initRig(await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).json());
} catch(error) {
    document.getElementById('status').textContent='Cannot load rigged body: '+error.message;
    throw error;
}
const skeleton=p=>state.version===2?rigSkeleton(p):legacySkeleton(p);
const mannequin=p=>state.version===2?rigMannequin(p):legacyMannequin(p);
const jointNames=()=>state.version===2?rigControls():Object.keys(JOINTS);

const $=id=>document.getElementById(id),colors=[0xff8d91,0x81bcff,0x94dd9d,0xffd27f,0xc3a0ff];
const messages={
 ko:{intro:'3D 마네킹으로 캐릭터 영역 마스크를 만듭니다. 구도 유도용이며 정확한 포즈를 보장하지 않습니다.',character:'캐릭터',add:'추가',copy:'복제',remove:'삭제',number:'프롬프트 번호',joint:'관절',rotate:'관절 회전',move:'인물 이동',height:'키 배율',width:'몸통 너비',preset:'포즈',setPose:'포즈 적용',resetPerson:'선택한 인물 초기화',camera:'카메라 / 캔버스',front:'정면',side:'측면',back:'후면',masks:'파이프 마스크',clipping:'화면 밖으로 나간 마스크만 잘라냅니다. 완전히 가려지면 보이는 마스크가 빌 수 있습니다. 인물의 좌우 위치가 바뀌어도 번호는 유지됩니다.',undo:'실행 취소',redo:'다시 실행',save:'장면 저장',load:'장면 불러오기',apply:'노드에 적용',help:'빈 공간 드래그: 카메라 회전 · 우클릭 드래그: 이동 · 휠: 확대 · 관절 선택 후 회전 고리 드래그. 현재 카메라로 마스크를 만듭니다.',full:'전체 실루엣 (겹침 유지)',visible:'보이는 실루엣 (가림 제거)',applied:'장면을 노드에 적용했습니다.',ready:'편집 후 노드에 적용하세요.'},
 ja:{intro:'3Dマネキンから人物マスクを作ります。構図の目安で、正確なポーズを保証しません。',character:'人物',add:'追加',copy:'複製',remove:'削除',number:'プロンプト番号',joint:'関節',rotate:'関節を回転',move:'人物を移動',height:'身長倍率',width:'体の幅',preset:'ポーズ',setPose:'ポーズを適用',resetPerson:'選択人物をリセット',camera:'カメラ / キャンバス',front:'正面',side:'側面',back:'背面',masks:'パイプのマスク',clipping:'キャンバス外のみ切り取ります。完全に隠れると可視マスクは空になります。左右が入れ替わっても人物番号は固定です。',undo:'元に戻す',redo:'やり直す',save:'シーンを保存',load:'シーンを開く',apply:'ノードに適用',help:'空白をドラッグ: カメラ回転 · 右ドラッグ: 移動 · ホイール: ズーム · 関節を選びリングで回転。現在のカメラでマスクを作ります。',full:'全体シルエット（重複）',visible:'可視シルエット（遮蔽）',applied:'シーンをノードに適用しました。',ready:'編集後、ノードに適用してください。'},
 zh:{intro:'使用3D人体生成角色区域遮罩。仅引导构图，不保证精确姿势。',character:'角色',add:'添加',copy:'复制',remove:'删除',number:'提示词编号',joint:'关节',rotate:'旋转关节',move:'移动人物',height:'身高倍率',width:'身体宽度',preset:'姿势',setPose:'应用姿势',resetPerson:'重置所选人物',camera:'相机 / 画布',front:'正面',side:'侧面',back:'背面',masks:'管道遮罩',clipping:'只裁剪画布之外的遮罩。完全遮挡时可见遮罩可能为空。人物交换左右位置也保持编号。',undo:'撤销',redo:'重做',save:'保存场景',load:'加载场景',apply:'应用到节点',help:'拖动空白：旋转相机 · 右键拖动：平移 · 滚轮：缩放 · 选择关节后拖动旋转环。使用当前相机生成遮罩。',full:'完整轮廓（保留重叠）',visible:'可见轮廓（排除遮挡）',applied:'已应用到节点。',ready:'编辑后应用到节点。'},
 'zh-TW':{intro:'使用3D人體產生角色區域遮罩。僅引導構圖，不保證精確姿勢。',character:'角色',add:'新增',copy:'複製',remove:'刪除',number:'提示詞編號',joint:'關節',rotate:'旋轉關節',move:'移動人物',height:'身高倍率',width:'身體寬度',preset:'姿勢',setPose:'套用姿勢',resetPerson:'重設所選人物',camera:'相機 / 畫布',front:'正面',side:'側面',back:'背面',masks:'管線遮罩',clipping:'只裁剪畫布外的遮罩。完全遮擋時可見遮罩可能為空。人物交換左右位置也保持編號。',undo:'復原',redo:'重做',save:'儲存場景',load:'載入場景',apply:'套用到節點',help:'拖動空白：旋轉相機 · 右鍵拖動：平移 · 滾輪：縮放 · 選取關節後拖動旋轉環。使用目前相機產生遮罩。',full:'完整輪廓（保留重疊）',visible:'可見輪廓（排除遮擋）',applied:'已套用到節點。',ready:'編輯後套用到節點。'},
};
let state=defaultRigScene(),selected=1,joint='left_elbow',mode='rotate',locale='en',history=[],future=[],rebuilding=false,dragging=false,initialized=false;
let previewTimer,previewRequest=0;
const person=()=>state.people.find(p=>p.id===selected),token=location.hash.slice(1);
const tell=(type,extra={})=>{if(parent!==window)parent.postMessage({type,token,...extra},location.origin);};
const status=s=>{$('status').textContent=s;};
const text=(key,fallback)=>messages[locale]?.[key]??fallback;
const scene=new T.Scene();scene.background=new T.Color(0x111923);
const camera=new T.PerspectiveCamera(38,1,.05,100);
const renderer=new T.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
$('viewport').append(renderer.domElement);
const orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=false;orbit.minDistance=.5;orbit.maxDistance=25;
orbit.minPolarAngle=.015;orbit.maxPolarAngle=Math.PI-.015;
const light=new T.HemisphereLight(0xffffff,0x465574,2.4);scene.add(light);
const grid=new T.GridHelper(10,20,0x607285,0x283747);grid.position.y=-.035;scene.add(grid);
const bodies=new T.Group(),handles=new T.Group();scene.add(bodies,handles);
const proxy=new T.Object3D();scene.add(proxy);
const gizmo=new TransformControls(camera,renderer.domElement);scene.add(gizmo.getHelper());gizmo.setSpace('local');gizmo.setSize(.8);
const sphereGeometry=new T.SphereGeometry(.025,10,6),handleMaterials=new Map();
const raycaster=new T.Raycaster(),pointer=new T.Vector2();let down=null;

function disposeMeshes(group){
    while(group.children.length){const child=group.children[0];group.remove(child);if(child.geometry!==sphereGeometry)child.geometry?.dispose();if(child.material&&!handleMaterials.has(child.material))child.material.dispose();}
}
function render(){renderer.render(scene,camera);}
function resize(){
    const host=$('viewport'),ratio=state.width/state.height;
    let w=Math.max(1,host.clientWidth-20),h=Math.max(1,host.clientHeight-20);
    if(w/h>ratio)w=h*ratio;else h=w/ratio;
    renderer.setSize(Math.round(w),Math.round(h));camera.aspect=ratio;camera.updateProjectionMatrix();render();
}
new ResizeObserver(resize).observe($('viewport'));
function setCamera(){camera.position.fromArray(state.camera.position);camera.fov=state.camera.fov;camera.updateProjectionMatrix();orbit.target.fromArray(state.camera.target);orbit.update();}
function readCamera(){
    const clean=v=>Number(v.toFixed(12));
    state.camera.position=camera.position.toArray().map(clean);state.camera.target=orbit.target.toArray().map(clean);state.camera.fov=camera.fov;
}
function saveHistory(){
    const raw=JSON.stringify(state);if(history.at(-1)!==raw){history.push(raw);if(history.length>40)history.shift();future=[];}
    $('undo').disabled=history.length<2;$('redo').disabled=!future.length;
    schedulePreview();
}
function undo(redo=false){
    if(redo){if(future.length)history.push(future.pop());}
    else if(history.length>1)future.push(history.pop());
    if(history.length){state=JSON.parse(history.at(-1));selected=state.people.some(p=>p.id===selected)?selected:state.people[0].id;setCamera();refresh();}
    $('undo').disabled=history.length<2;$('redo').disabled=!future.length;
    schedulePreview();
}
function placeGizmo(){
    if(dragging)return;
    const p=person(),{points,frames}=skeleton(p),r=frames[joint];
    proxy.position.fromArray(mode==='translate'?points.pelvis:points[joint]);
    const matrix=new T.Matrix4().set(r[0][0],r[0][1],r[0][2],0,r[1][0],r[1][1],r[1][2],0,r[2][0],r[2][1],r[2][2],0,0,0,0,1);
    proxy.quaternion.setFromRotationMatrix(matrix);proxy.updateMatrixWorld(true);gizmo.attach(proxy);gizmo.setMode(mode);
    gizmo.setSpace(mode==='translate'?'world':'local');
}
function build(){
    rebuilding=true;disposeMeshes(bodies);disposeMeshes(handles);
    for(const p of state.people){
        const {vertices,faces,points}=mannequin(p),geo=new T.BufferGeometry();
        geo.setAttribute('position',new T.Float32BufferAttribute(vertices.flat(),3));geo.setIndex(faces.flat());geo.computeVertexNormals();
        const mesh=new T.Mesh(geo,new T.MeshLambertMaterial({color:colors[(p.id-1)%5],side:T.DoubleSide}));mesh.userData={id:p.id,joint:'pelvis'};bodies.add(mesh);
        for(const [name,point] of Object.entries(points)){
            const color=p.id===selected&&name===joint?0xffffff:p.id===selected?0xffdf91:0x445568;
            let mat=handleMaterials.get(color);if(!mat){mat=new T.MeshBasicMaterial({color,depthTest:false});handleMaterials.set(color,mat);handleMaterials.set(mat,mat);}
            const h=new T.Mesh(sphereGeometry,mat);h.position.fromArray(point);h.renderOrder=2;h.userData={id:p.id,joint:name};handles.add(h);
        }
    }
    rebuilding=false;placeGizmo();render();
}
function controls(){
    const p=person();
    if(!jointNames().includes(joint))joint='pelvis';
    $('joint').replaceChildren(...jointNames().map(n=>new Option(n.replaceAll('_',' '),n)));
    $('outline').checked=state.outline??false;$('outline').disabled=state.version!==2;
    $('person').replaceChildren(...state.people.map(p=>new Option(String(p.id),String(p.id))));$('person').value=String(selected);
    $('number').value=selected;$('joint').value=joint;
    for(const k of ['scale','bulk']){$(k).value=p[k];$(k+'-value').textContent=p[k].toFixed(2);}
    const angles=p.joints[joint]??[0,0,0];for(let i=0;i<3;i++){$('angle'+i).value=angles[i];$('angle-value'+i).textContent=Math.round(angles[i]);}
    $('width').value=state.width;$('height').value=state.height;$('fov').value=state.camera.fov;$('fov-value').textContent=Math.round(state.camera.fov);
    $('mask-mode').value=state.mask_mode;$('remove').disabled=state.people.length===1;
    $('add').disabled=$('copy').disabled=state.people.length===10;
    $('rotate').classList.toggle('active',mode==='rotate');$('move').classList.toggle('active',mode==='translate');
}
function refresh(){controls();build();resize();}
function mutate(fn){fn();refresh();saveHistory();}

orbit.addEventListener('change',()=>{if(!rebuilding){readCamera();render();}});
orbit.addEventListener('end',()=>{readCamera();saveHistory();});
gizmo.addEventListener('change',render);
gizmo.addEventListener('dragging-changed',event=>{dragging=event.value;orbit.enabled=!dragging;if(!dragging){saveHistory();placeGizmo();render();}});
gizmo.addEventListener('objectChange',()=>{
    if(rebuilding)return;
    const p=person();
    if(mode==='translate')p.position=sub(proxy.position.toArray(),sub(skeleton(p).points.pelvis,p.position)).map(v=>Math.max(-10,Math.min(10,v)));
    else{
        const sk=skeleton(p);
        const parentJoint=state.version===2?null:JOINTS[joint][0];
        const parentR=state.version===2?sk.baseFrames[joint]:(parentJoint?sk.frames[parentJoint]:rotation(p.rotation));
        const worldR=new T.Matrix4().makeRotationFromQuaternion(proxy.quaternion).elements;
        const world=[[worldR[0],worldR[4],worldR[8]],[worldR[1],worldR[5],worldR[9]],[worldR[2],worldR[6],worldR[10]]];
        const local=mm(parentR[0].map((_,i)=>parentR.map(row=>row[i])),world);
        const m=new T.Matrix4().set(...[...local[0],0,...local[1],0,...local[2],0,0,0,0,1]);
        const e=new T.Euler().setFromRotationMatrix(m,state.version===2?'ZYX':'XYZ');p.joints[joint]=[e.x,e.y,e.z].map(v=>v*180/Math.PI);
    }
    build();controls();
});
renderer.domElement.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY];});
renderer.domElement.addEventListener('pointerup',e=>{
    if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>4||gizmo.axis||dragging)return;
    const rect=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1);
    raycaster.setFromCamera(pointer,camera);
    const hit=raycaster.intersectObjects(handles.children)[0]??raycaster.intersectObjects(bodies.children)[0];
    if(hit){selected=hit.object.userData.id;joint=hit.object.userData.joint;refresh();}
});
$('joint').replaceChildren(...Object.keys(JOINTS).map(n=>new Option(n.replaceAll('_',' '),n)));
for(let i=0;i<3;i++){
    const label=document.createElement('label');label.innerHTML=`<span>${'XYZ'[i]}</span><input id="angle${i}" type="range" min="-180" max="180" step="1"><output id="angle-value${i}"></output>`;$('angles').append(label);
    $('angle'+i).oninput=()=>{const p=person();p.joints[joint]??=[0,0,0];p.joints[joint][i]=Number($('angle'+i).value);build();controls();};
    $('angle'+i).onchange=saveHistory;
}
$('person').onchange=()=>{selected=Number($('person').value);refresh();};
$('joint').onchange=()=>{joint=$('joint').value;mode='rotate';refresh();};
$('number').onchange=()=>{
    const n=Number($('number').value);if(!Number.isInteger(n)||n<1||n>10||state.people.some(p=>p.id===n&&p!==person())){status('Choose an unused character number 1–10.');controls();return;}
    mutate(()=>{person().id=n;selected=n;state.people.sort((a,b)=>a.id-b.id);});
};
function addPerson(copy){
    if(state.people.length>=10)return;
    const id=Array.from({length:10},(_,i)=>i+1).find(n=>!state.people.some(p=>p.id===n));
    mutate(()=>{const p=structuredClone(copy?person():(state.version===2?defaultPerson():defaultScene().people[0]));p.id=id;p.position[0]=Math.min(9,p.position[0]+.5);state.people.push(p);state.people.sort((a,b)=>a.id-b.id);selected=id;});
}
$('add').onclick=()=>addPerson(false);$('copy').onclick=()=>addPerson(true);
$('remove').onclick=()=>{if(state.people.length>1)mutate(()=>{state.people=state.people.filter(p=>p.id!==selected);selected=state.people[0].id;});};
for(const [id,value] of [['rotate','rotate'],['move','translate']])$(id).onclick=()=>{mode=value;refresh();};
for(const key of ['scale','bulk']){$(key).oninput=()=>{person()[key]=Number($(key).value);refresh();};$(key).onchange=saveHistory;}
$('pose').onclick=()=>mutate(()=>{
    const presets={standing:{},wave:{left_shoulder:[0,0,-145],left_elbow:[-25,0,0]},
        seated:{right_hip:[-90,0,0],left_hip:[-90,0,0],right_knee:[90,0,0],left_knee:[90,0,0]},
        reach:{right_shoulder:[-80,0,-15],left_shoulder:[-80,0,15],right_elbow:[-15,0,0],left_elbow:[-15,0,0]}};
    person().joints=state.version===2?preset($('preset').value):structuredClone(presets[$('preset').value]);
});
$('reset-person').onclick=()=>mutate(()=>{person().joints=state.version===2?preset('standing'):{};person().rotation=[0,0,0];person().scale=1;person().bulk=1;});
for(const [id,offset] of [['front',[0,.25,4.1]],['side',[4.1,.25,0]],['back',[0,.25,-4.1]]])$(id).onclick=()=>mutate(()=>{
    state.camera.position=state.camera.target.map((v,i)=>v+offset[i]);setCamera();
});
$('fov').oninput=()=>{state.camera.fov=Number($('fov').value);camera.fov=state.camera.fov;camera.updateProjectionMatrix();controls();render();};$('fov').onchange=saveHistory;
for(const key of ['width','height'])$(key).onchange=()=>{
    const v=Number($(key).value);if(!Number.isInteger(v)||v<64||v>2048){status('Use 64–2048 pixels per side.');controls();return;}mutate(()=>{state[key]=v;});
};
$('outline').onchange=()=>mutate(()=>{state.outline=$('outline').checked;});
$('mask-mode').onchange=()=>mutate(()=>{state.mask_mode=$('mask-mode').value;});
$('undo').onclick=()=>undo();$('redo').onclick=()=>undo(true);
$('save').onclick=()=>{
    readCamera();const url=URL.createObjectURL(new Blob([JSON.stringify(state,null,2)],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download='RS-3D-Pose-Scene.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
$('load').onclick=()=>$('file').click();
async function validate(raw){
    const response=await fetch(new URL('../../../rs_mc/pose3d/preview',location.href).pathname,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(raw)});
    const data=await response.json();if(!response.ok)throw Error(data.error??'Invalid 3D scene.');return data;
}
function schedulePreview(){
    clearTimeout(previewTimer);const request=++previewRequest;
    previewTimer=setTimeout(async()=>{
        try{
            const data=await validate(state);if(request!==previewRequest)return;
            const canvas=$('mask-preview'),ctx=canvas.getContext('2d');canvas.height=Math.round(canvas.width*state.height/state.width);
            ctx.fillStyle='#171c25';ctx.fillRect(0,0,canvas.width,canvas.height);
            for(const m of data.masks){
                ctx.fillStyle='#'+colors[(m.number-1)%5].toString(16).padStart(6,'0')+'99';
                for(let y=0;y<m.height;y++)for(let x=0;x<m.width;x++)if(m.data[y*m.width+x])ctx.fillRect(x*canvas.width/m.width,y*canvas.height/m.height,Math.ceil(canvas.width/m.width),Math.ceil(canvas.height/m.height));
                ctx.fillStyle='white';ctx.font='bold 14px sans-serif';ctx.fillText(String(m.number),m.center[0]*canvas.width,m.center[1]*canvas.height);
            }
        }catch(e){if(request===previewRequest)status(e.message);}
    },300);
}
$('file').onchange=async()=>{
    const file=$('file').files[0];if(!file)return;
    try{if(file.size>100000)throw Error('Scene must be under 100 KB.');const raw=JSON.parse(await file.text());const data=await validate(raw);state=data.scene;selected=state.people[0].id;setCamera();refresh();saveHistory();status(text('ready','Edit the scene, then Apply.'));}catch(e){status(e.message);}finally{$('file').value='';}
};
$('apply').onclick=async()=>{
    $('apply').disabled=true;
    try{readCamera();const data=await validate(state);tell('rs-pose3d-apply',{scene:state,preview:data});status(text('applied','Scene applied to node.'));}
    catch(e){status(e.message);}finally{$('apply').disabled=false;}
};
window.addEventListener('message',event=>{
    if(event.source!==parent||event.origin!==location.origin||event.data?.token!==token)return;
    if(event.data.type==='rs-pose3d-init'&&!initialized){
        initialized=true;history=[];future=[];state=structuredClone(event.data.scene);selected=state.people[0].id;locale=/^zh[-_](TW|HK|Hant)/i.test(event.data.locale??'')?'zh-TW':(event.data.locale??'en').split(/[-_]/)[0];
        document.documentElement.lang=locale;
        for(const el of document.querySelectorAll('[data-i18n]'))el.textContent=text(el.dataset.i18n,el.textContent);
        for(const [value,key] of [['full','full'],['visible','visible']])$('mask-mode').querySelector(`[value="${value}"]`).textContent=text(key,$('mask-mode').querySelector(`[value="${value}"]`).textContent);
        setCamera();refresh();saveHistory();status(text('ready','Edit the scene, then Apply.'));
    }else if(event.data.type==='rs-pose3d-error')status(event.data.error);
});
window.addEventListener('pagehide',()=>{gizmo.dispose();orbit.dispose();disposeMeshes(bodies);disposeMeshes(handles);sphereGeometry.dispose();renderer.dispose();});
setCamera();refresh();saveHistory();tell('rs-pose3d-ready');
