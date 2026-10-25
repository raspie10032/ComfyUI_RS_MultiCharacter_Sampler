// SPDX-License-Identifier: GPL-3.0-only
import { chineseLocale, chineseText } from "./i18n.js";
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const widget = (node, name) => node.widgets?.find(w => w.name === name);
const val = (node, name, fallback) => widget(node, name)?.value ?? fallback;
const language = () => String(app.extensionManager?.setting?.get?.("Comfy.Locale") ?? globalThis.navigator?.language ?? "en");
const text = (en, ko, ja) => chineseLocale(language()) ? chineseText(en, language()) : language().startsWith("ko") ? ko : language().startsWith("ja") ? ja : en;

export function maskPlacements(node) {
    try { return JSON.parse(val(node, "mask_transforms", "{}")); } catch { return {}; }
}

export function movedBox(slot, dx, dy) {
    const width = clamp(Number(slot.width), .01, 1), height = clamp(Number(slot.height), .01, 1);
    return { x: clamp(Number(slot.x) + dx, width / 2, 1 - width / 2),
        y: clamp(Number(slot.y) + dy, height / 2, 1 - height / 2) };
}

export function resizedBox(slot, x, y) {
    return { width: clamp(2 * Math.abs(x - slot.x), .01, Math.max(.01, 2 * Math.min(slot.x, 1 - slot.x))),
        height: clamp(2 * Math.abs(y - slot.y), .01, Math.max(.01, 2 * Math.min(slot.y, 1 - slot.y))) };
}

export function supportBounds(mask) {
    if (!mask || mask.empty) return null;
    let left = mask.width, right = 0, top = mask.height, bottom = 0;
    for (let y = 0; y < mask.height; y++) for (let x = 0; x < mask.width; x++) if (mask.data[y * mask.width + x]) {
        left = Math.min(left, x); right = Math.max(right, x + 1);
        top = Math.min(top, y); bottom = Math.max(bottom, y + 1);
    }
    return right ? [left / mask.width, top / mask.height, right / mask.width, bottom / mask.height] : null;
}

// The reference is a display-only descriptor from the drawing node. No pixels
// or transform edits are written back to that upstream node.
function reference(node) {
    const seen = new Set();
    while (node && !seen.has(node)) {
        seen.add(node);
        if ((node.comfyClass ?? node.type) === "RSMultiCharacterMaskDraw" && node.mode !== 4) {
            try { return JSON.parse(val(node, "drawing", "{}")).background ?? null; } catch { return null; }
        }
        const i = node.inputs?.findIndex(v => v.name === "building_pipe") ?? -1;
        node = node.getInputNode?.((node.comfyClass ?? node.type) === "Reroute" ? 0 : i);
    }
    return null;
}

export function addPositionEditor(node, { collectSlots, editorSource = n => n, centersFor, colors }) {
    if (node.rsPositionEditor) return;
    node.rsPositionEditor = true;
    const storage = widget(node, "mask_transforms");
    if (storage) { storage.hidden = true; storage.type = "rs-mc-hidden"; storage.computeSize = () => [0, -4]; }
    const root = document.createElement("div");
    root.className = "rs-mc-position-editor";
    root.style.cssText = "box-sizing:border-box;padding:8px;background:#202630;color:#eee;font:12px sans-serif;pointer-events:auto;height:100%;overflow:auto";
    for (const event of ["pointerdown", "wheel", "keydown"]) root.addEventListener(event, e => e.stopPropagation());
    const toolbar = document.createElement("div");
    toolbar.style.cssText = "display:flex;gap:6px;align-items:center;margin-bottom:7px;flex-wrap:wrap";
    const label = document.createElement("label");
    label.textContent = text("Edit region", "조절할 영역", "編集する領域");
    const select = document.createElement("select");
    select.setAttribute("aria-label", label.textContent);
    select.style.cssText = "max-width:100%;background:#343e4e;color:white;border:1px solid #617087;padding:4px";
    label.append(select); toolbar.append(label); root.append(toolbar);
    const buttons = [];
    const button = (caption, action) => {
        const b = document.createElement("button"); b.type = "button"; b.textContent = caption;
        b.style.cssText = "background:#343e4e;color:white;border:1px solid #617087;border-radius:4px;padding:4px 7px";
        b.onclick = action; toolbar.append(b); buttons.push(b); return b;
    };
    const canvas = document.createElement("canvas");
    canvas.setAttribute("aria-label", text("Regional layout", "영역 배치도", "領域配置図"));
    canvas.style.cssText = "display:block;width:100%;height:auto;max-height:320px;object-fit:contain;background:#111820;touch-action:none;cursor:move";
    const status = document.createElement("div"); status.style.cssText = "margin-top:6px;line-height:1.5;white-space:pre-line";
    root.append(canvas, status);
    let active = null, drag = null, dirty = false, frame = 0, disposed = false;
    let background = null, refKey = "", generation = 0, previousState = "", optionsKey = "";
    const undo = [];
    const maskIds = new WeakMap(); let nextMaskId = 0;
    const maskId = mask => { if (!mask) return 0; if (!maskIds.has(mask)) maskIds.set(mask, ++nextMaskId); return maskIds.get(mask); };
    const state = () => JSON.stringify(node.widgets.filter(w => /^character\d+_(?:x|y|width|height)$/.test(w.name) || w.name === "mask_transforms").map(w => [w.name, w.value]));
    const restore = serialized => { for (const [name, value] of JSON.parse(serialized)) if (widget(node, name)) widget(node, name).value = value; };
    const changed = () => { node.graph?.change?.(); node.setDirtyCanvas(true, true); schedule(); };
    function begin() { node.graph?.beforeChange?.(); previousState = state(); }
    function finish(cancel = false) {
        if (!drag && !dirty) return;
        if (cancel) restore(previousState);
        else if (state() !== previousState) { undo.push(previousState); if (undo.length > 30) undo.shift(); }
        drag = null; dirty = false; node.graph?.afterChange?.(); changed();
    }
    button(text("Undo", "되돌리기", "元に戻す"), () => {
        finish(); if (!undo.length) return;
        node.graph?.beforeChange?.(); restore(undo.pop()); node.graph?.afterChange?.(); changed();
    });
    button(text("Reset selected", "선택 배치 초기화", "選択をリセット"), () => {
        const slot = selected(); if (!slot || locked()) return;
        begin(); dirty = true;
        if (slot.masked) setMask(slot.id, [0, 0, 1]);
        else setFields(slot.id, slot.geometry === "box" ? {x:.5,y:.5,width:.4,height:.8} : {x:.5,y:.5});
        finish();
    });
    function setFields(id, changes) {
        for (const [name, value] of Object.entries(changes)) {
            const w = widget(node, `character${id}_${name}`); if (w) w.value = Math.round(value * 10000) / 10000;
        }
    }
    function setMask(id, value) {
        if (storage) storage.value = JSON.stringify({...maskPlacements(node), [id]:value.map(v => Math.round(v * 10000) / 10000)});
    }
    function selected() { return collectSlots(node).slots.find(s => s.id === active); }
    function locked() {
        const data = collectSlots(node), slot = data.slots.find(s => s.id === active);
        return data.unknown || !slot || slot.dynamic || (slot.masked && !slot.maskOriginal);
    }
    select.onchange = () => { finish(); active = Number(select.value); schedule(); };
    function resizeSelected(factor) {
        const s = selected(); if (!s || locked() || (!s.masked && s.geometry !== "box")) return;
        begin(); dirty = true;
        if (s.masked) { const [x,y,scale] = s.maskTransform ?? [0,0,1]; setMask(s.id, [x,y,clamp(scale*factor,.05,4)]); }
        else setFields(s.id, {width:clamp(s.width*factor,.01,Math.max(.01,2*Math.min(s.x,1-s.x))),height:clamp(s.height*factor,.01,Math.max(.01,2*Math.min(s.y,1-s.y)))});
        finish();
    }
    const smaller = button("−", () => resizeSelected(1/1.1)), larger = button("+", () => resizeSelected(1.1));
    smaller.setAttribute("aria-label", text("Shrink selected", "선택 영역 축소", "選択を縮小"));
    larger.setAttribute("aria-label", text("Enlarge selected", "선택 영역 확대", "選択を拡大"));
    function bounds(s) {
        return s.masked ? supportBounds(s.maskSupport) : s.geometry === "box" ? [s.x-s.width/2,s.y-s.height/2,s.x+s.width/2,s.y+s.height/2] : null;
    }
    function position(event) {
        const rect = canvas.getBoundingClientRect();
        // Canvas CSS aspect ratio matches its bitmap, so graph zoom is handled
        // by the browser's rect. Do not use offsetX or LiteGraph scale here.
        return [(event.clientX-rect.left)/rect.width, (event.clientY-rect.top)/rect.height];
    }
    canvas.onpointerdown = event => {
        if (event.button !== 0 || locked()) return;
        const s = selected(); if (!s) return;
        const p = position(event), b = bounds(s), rect = canvas.getBoundingClientRect();
        const resize = b && Math.hypot((p[0]-b[2])*rect.width,(p[1]-b[3])*rect.height) < 14;
        begin(); dirty = true; drag = {slot:s,start:p,resize,pointer:event.pointerId};
        canvas.setPointerCapture(event.pointerId); event.preventDefault();
        if (!s.masked && s.geometry === "point") { setFields(s.id,{x:clamp(p[0],0,1),y:clamp(p[1],0,1)}); changed(); }
    };
    canvas.onpointermove = event => {
        if (!drag || event.pointerId !== drag.pointer) return;
        const {slot:s,start,resize} = drag;
        const p = position(event), dx = p[0]-start[0], dy = p[1]-start[1];
        if (s.masked) {
            const [x,y,scale] = s.maskTransform ?? [0,0,1];
            if (resize) {
                const center = [s.maskOriginal.center[0]+x,s.maskOriginal.center[1]+y];
                const ratio = Math.hypot(p[0]-center[0],p[1]-center[1]) / Math.max(.001,Math.hypot(start[0]-center[0],start[1]-center[1]));
                setMask(s.id,[x,y,clamp(scale*ratio,.05,4)]);
            } else setMask(s.id,[clamp(x+dx,-1,1),clamp(y+dy,-1,1),scale]);
        } else if (s.geometry === "box") setFields(s.id,resize ? resizedBox(s,...p) : movedBox(s,dx,dy));
        else setFields(s.id,{x:clamp(p[0],0,1),y:clamp(p[1],0,1)});
        changed();
    };
    canvas.onpointerup = event => { if (drag?.pointer === event.pointerId) { finish(); if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId); } };
    canvas.onpointercancel = () => finish(true);
    canvas.onlostpointercapture = () => finish();
    root.onkeydown = event => { if (event.key === "Escape") { finish(true); event.preventDefault(); } };
    function schedule() { if (!frame && !disposed) frame = requestAnimationFrame(() => { frame = 0; refresh(); }); }
    function refresh() {
        if (disposed) return;
        const {slots,unknown,cameraPending} = collectSlots(node), centers = centersFor(slots);
        const count = Number(val(node,"character_count",2));
        const editable = slots.filter(s => s.id <= count);
        const kind = s => s.masked ? text("Mask","마스크","マスク") : s.geometry === "box" ? text("Box","박스","ボックス") : text("Point","포인트","点");
        const key = JSON.stringify(editable.map(s=>[s.id,kind(s)]));
        if (key !== optionsKey) {
            optionsKey = key; select.replaceChildren(...editable.map(s=>{
                const option=document.createElement("option"); option.value=String(s.id); option.textContent=`${s.id} · ${kind(s)}${s.kind==="text" ? text(" · Text"," · 글자"," · 文字") : ""}`;return option;
            }));
            if (!editable.some(s=>s.id===active)) active=editable[0]?.id ?? null;
            select.value=String(active);
        }
        const descriptor = reference(editorSource(node)), newKey = JSON.stringify(descriptor);
        if (refKey !== newKey) {
            refKey=newKey; background=null; const token=++generation;
            if (descriptor?.filename) {
                const image=new Image();
                image.onload=()=>{if(token===generation && !disposed){background=image;schedule();}};
                image.src=api.apiURL(`/view?${new URLSearchParams(descriptor)}`);
            }
        }
        const selectedSlot=editable.find(s=>s.id===active), disabled=locked();
        smaller.disabled=larger.disabled=disabled || (!selectedSlot?.masked && selectedSlot?.geometry!=="box");
        buttons[1].disabled=disabled; select.disabled=!editable.length || !!drag;
        // Use the drawing/reference aspect rather than distort human shapes.
        const support=slots.find(s=>s.maskOriginal)?.maskOriginal;
        const aspect=support ? support.width/support.height : background ? background.naturalWidth/background.naturalHeight : 1;
        const width=512, height=Math.round(width/clamp(aspect,.25,4));
        const stamp=JSON.stringify([slots.map(s=>[s.id,s.geometry,s.x,s.y,s.width,s.height,s.dynamic,s.kind,s.masked,maskId(s.maskSupport)]),unknown,cameraPending,active,disabled,!!background,width,height,language()]);
        if (stamp===canvas.rsStamp) return;
        canvas.rsStamp=stamp; canvas.width=width; canvas.height=height;
        // Avoid object-fit letterboxing: events map directly onto the bitmap.
        canvas.style.maxHeight="none"; canvas.style.width=`min(100%, ${Math.round(320*aspect)}px)`; canvas.style.margin="auto";
        const ctx=canvas.getContext("2d"); ctx.fillStyle="#111820";ctx.fillRect(0,0,width,height);
        if(background){ctx.globalAlpha=.55;ctx.drawImage(background,0,0,width,height);ctx.globalAlpha=1;}
        if(!unknown) for(let row=0;row<64;row++) for(let col=0;col<64;col++){
            const x=(col+.5)/64,y=(row+.5)/64;
            let ids=slots.map((s,i)=>s.masked ? s.maskSupport?.data[Math.min(s.maskSupport.height-1,Math.floor(y*s.maskSupport.height))*s.maskSupport.width+Math.min(s.maskSupport.width-1,Math.floor(x*s.maskSupport.width))]?i:-1 : s.geometry==="box"&&Math.abs(x-s.x)<=s.width/2&&Math.abs(y-s.y)<=s.height/2?i:-1).filter(i=>i>=0);
            if(!ids.length){const points=slots.map((s,i)=>!s.masked&&s.geometry==="point"?i:-1).filter(i=>i>=0);if(points.length)ids=[points.reduce((a,b)=>Math.hypot(x-centers[a][0],y-centers[a][1])<=Math.hypot(x-centers[b][0],y-centers[b][1])?a:b)];}
            for(const i of ids){ctx.fillStyle=colors[(slots[i].id-1)%10];ctx.globalAlpha=(slots[i].id === active ? .42 : .18)/ids.length;ctx.fillRect(col*width/64,row*height/64,width/64+.5,height/64+.5);}
        }
        ctx.globalAlpha=1;ctx.font="bold 17px sans-serif";
        slots.forEach((s,i)=>{
            if(s.masked&&(!s.maskSupport||s.maskSupport.empty))return;
            const [x,y]=centers[i],b=bounds(s);ctx.strokeStyle=ctx.fillStyle=colors[(s.id-1)%10];ctx.lineWidth=s.id===active?3:1;
            if(b){ctx.setLineDash(s.id===active?[]:[4,4]);ctx.strokeRect(b[0]*width,b[1]*height,(b[2]-b[0])*width,(b[3]-b[1])*height);ctx.setLineDash([]);if(s.id===active)ctx.fillRect(b[2]*width-5,b[3]*height-5,10,10);}
            ctx.beginPath();ctx.arc(x*width,y*height,s.id===active?6:3,0,2*Math.PI);ctx.fill();
            ctx.fillText(String(s.id),clamp(x*width+9,0,width-22),clamp(y*height-8,18,height));
        });
        status.textContent=disabled ? text("Linked or unready values: edit the source or run the mask first.","연결값·미준비 마스크: 원본 입력을 조절하거나 마스크를 먼저 실행하세요.","接続値・未準備のマスク：元の入力を編集するか先に実行してください。") : text("Select a number above, then drag. Corner/−/+ resizes boxes and masks. Mask overflow is clipped; layout is approximate.","위에서 번호 선택 → 드래그로 이동. 모서리·−/+로 박스·마스크 크기 조절. 캔버스 밖 마스크는 잘리며 배치는 대략 유도합니다.","上で番号を選んでドラッグ。角・−/+で矩形・マスクを拡縮。外側のマスクは切り取り、配置は目安です。");
        if(selectedSlot?.masked && selectedSlot.maskSupport?.empty)status.textContent=text("Mask is outside the canvas. Move it back, enlarge it, or reset placement.","마스크가 캔버스 밖입니다. 안으로 옮기거나 확대·초기화하세요.","マスクがキャンバス外です。戻す・拡大・リセットしてください。");
        if(cameraPending && !disabled) status.textContent += " " + text("Editing before camera; see Finalize for its result.","카메라 적용 전 배치입니다. 적용 결과는 최종 파이프에서 확인하세요.","カメラ適用前の配置です。結果は最終パイプで確認してください。");
    }
    const dom=node.addDOMWidget("rs_mc_position_editor","rs_mc_position_editor",root,{serialize:false,hideOnZoom:false});
    dom.computeSize=()=>[300,500]; dom.serialize=false; dom.serializeValue=()=>undefined;
    const draw=node.onDrawBackground;
    node.onDrawBackground=function(){const result=draw?.apply(this,arguments);schedule();return result;};
    const removed=node.onRemoved;
    node.onRemoved=function(){disposed=true;generation++;if(frame)cancelAnimationFrame(frame);finish(true);return removed?.apply(this,arguments);};
    schedule();
}
