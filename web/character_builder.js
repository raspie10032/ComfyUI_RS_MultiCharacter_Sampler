import { app } from "../../scripts/app.js";

const roles = new Set(["RSMultiCharacterPrompt", "RSMultiCharacterLoRA", "RSMultiCharacterPosition"]);
const finalType = "RSMultiCharacterFinalize";
const colors = ["#ff8d91", "#81bcff", "#94dd9d", "#ffd27f", "#c3a0ff", "#7fe5df", "#f5a6d8", "#cedd78", "#c7b6a2", "#e0e5ed"];
const typeOf = node => node.comfyClass ?? node.type;
const value = (node, name, fallback) => node.widgets?.find(w => w.name === name)?.value ?? fallback;

function inputNode(node, name) {
    const index = node.inputs?.findIndex(i => i.name === name) ?? -1;
    if (index < 0) return null;
    return node.getInputNode?.(index) ?? null;
}

// Diagram only: never evaluates arbitrary STRING-producing nodes or changes prompts.
export function collectSlots(node) {
    const chain = [], seen = new Set();
    let unknown = false;
    while (node && !seen.has(node)) {
        seen.add(node);
        const type = typeOf(node);
        if (roles.has(type)) {
            if (node.mode !== 4) chain.push(node); // Match ComfyUI bypass.
            node = inputNode(node, "building_pipe");
        } else if (type === finalType) node = inputNode(node, "building_pipe");
        else if (type === "Reroute") node = node.getInputNode?.(0);
        else { unknown = true; break; }
    }
    const slots = new Map();
    let promptCount = null, lastCount = 0;
    for (const item of chain.reverse()) {
        const count = Number(value(item, "character_count", 2));
        lastCount = Math.max(lastCount, count);
        const type = typeOf(item);
        if (type === "RSMultiCharacterPrompt") promptCount = count;
        if (inputNode(item, "character_count") || item.mode === 2) unknown = true;
        for (let id=1; id<=10; id++) {
            const slot = slots.get(id) ?? {id, enabled:true, kind:"character", geometry:"point", x:.5, y:.5, width:.4, height:.8};
            const key = suffix => `character${id}${suffix}`;
            if (type === "RSMultiCharacterPrompt") {
                slot.enabled = id<=count && value(item,key("_enable"),true);
                slot.kind = value(item,key("_kind"),"character");
                slot.promptConnected = !!inputNode(item,key(""));
                if (["_enable","_kind"].some(k=>inputNode(item,key(k)))) unknown = true;
            }
            if (type === "RSMultiCharacterPosition") {
                for (const [k,d] of Object.entries({geometry:"point",x:.5,y:.5,width:.4,height:.8})) slot[k] = id<=count ? value(item,key("_"+k),d) : d;
                slot.dynamic = id<=count && ["geometry","x","y","width","height"].some(k=>!!inputNode(item,key("_"+k)));
            }
            slots.set(id,slot);
        }
    }
    return {slots:[...slots.values()].filter(s=>s.id<=(promptCount??lastCount) && s.enabled),unknown};
}

export function centersFor(slots) {
    const centers = slots.map(s => [Number(s.x), Number(s.y)]);
    const points = slots.map((s,i) => s.geometry === "point" ? i : -1).filter(i => i >= 0);
    const groups = new Map();
    for (const i of points) {
        const key = JSON.stringify(centers[i]);
        groups.set(key, [...(groups.get(key) ?? []), i]);
    }
    for (const group of groups.values()) {
        if (group.length < 2) continue;
        const [x,y] = centers[group[0]];
        // Distances use original points, matching layout.effective_centers.
        const others = points.filter(i => !group.includes(i)).map(i => [Number(slots[i].x), Number(slots[i].y)]);
        const radius = others.length ? Math.min(.25, ...others.map(([a,b]) => Math.hypot(x-a,y-b)/3)) : .5;
        const left = others.length ? Math.max(0,x-radius) : 0;
        const right = others.length ? Math.min(1,x+radius) : 1;
        group.forEach((i,j) => { centers[i] = [left+(right-left)*(j+.5)/group.length,y]; });
    }
    return centers;
}

function labels() {
    const lang = app.extensionManager?.setting?.get?.("Comfy.Locale") ?? globalThis.navigator?.language ?? "en";
    if (lang.startsWith("ko")) return ["예상 배치 · XY 0–1", "번호별 설정 · 최종 구도 보장 아님", "연결값 확인 필요: 생성 시 좌표 결정", "프롬프트 연결 대기: "];
    if (lang.startsWith("ja")) return ["配置の目安 · XY 0–1", "番号別設定 · 最終構図の保証ではありません", "接続値の確認が必要です", "プロンプト未接続: "];
    return ["Layout guide · XY 0–1", "By number · composition is approximate", "Linked values: layout resolved at execution", "Prompt connection missing: "];
}

function addDiagram(node) {
    node.addCustomWidget({
        name: "rs_mc_build_layout", type: "rs_mc_display", serialize: false,
        options: { serialize: false }, serializeValue: () => undefined,
        computeSize: () => [300, 254],
        draw(ctx, node, width, y) {
            const { slots, unknown } = collectSlots(node), centers = centersFor(slots);
            const text = labels(), left = 16, top = y+28, w = width-32, h = 176;
            ctx.save();
            ctx.font = "12px sans-serif"; ctx.fillStyle = "#d1d8e2"; ctx.fillText(text[0], left, y+16);
            ctx.fillStyle = "#171d27"; ctx.fillRect(left, top, w, h);
            const dynamic = unknown || slots.some(s => s.dynamic);
            const points = slots.map((s,i) => s.geometry === "point" ? i : -1).filter(i => i>=0);
            // Schematic partitions. Box coverage overrides point coverage, as in sampling.
            if (!dynamic) for (let row=0; row<32; row++) for (let col=0; col<48; col++) {
                const x=(col+.5)/48, cy=(row+.5)/32;
                let ids=slots.map((s,i) => s.geometry === "box" && Math.abs(x-s.x)<=s.width/2 && Math.abs(cy-s.y)<=s.height/2 ? i : -1).filter(i=>i>=0);
                if (!ids.length && points.length) ids=[points.reduce((a,b)=>Math.hypot(x-centers[a][0],cy-centers[a][1])<=Math.hypot(x-centers[b][0],cy-centers[b][1])?a:b)];
                for (const i of ids) {
                    ctx.fillStyle=colors[(slots[i].id-1)%10]; ctx.globalAlpha=.22/ids.length;
                    ctx.fillRect(left+col*w/48,top+row*h/32,w/48+.5,h/32+.5);
                }
            }
            ctx.globalAlpha=1; ctx.strokeStyle="#66768f"; ctx.strokeRect(left,top,w,h);
            if (!dynamic) slots.forEach((s,i)=>{
                const [x,cy]=centers[i], box=s.geometry==="box";
                const invalid=box && (x-s.width/2<0 || x+s.width/2>1 || cy-s.height/2<0 || cy+s.height/2>1);
                ctx.strokeStyle=ctx.fillStyle=invalid?"#ff4b4b":colors[(s.id-1)%10];
                if (box) ctx.strokeRect(left+(x-s.width/2)*w,top+(cy-s.height/2)*h,s.width*w,s.height*h);
                ctx.beginPath();ctx.arc(left+x*w,top+cy*h,3,0,Math.PI*2);ctx.fill();
                ctx.fillText(`${s.id}${s.kind==="text"?" T":""}`,Math.min(left+x*w+6,left+w-24),Math.max(top+12,top+cy*h-6));
            });
            ctx.fillStyle="#b4bdcc";ctx.fillText(dynamic?text[2]:text[1],left,top+h+18,width-32);
            const missing=slots.filter(s=>!s.promptConnected).map(s=>s.id);
            if(missing.length) {ctx.fillStyle="#ffd27f";ctx.fillText(text[3]+missing.join(", "),left,top+h+36,width-32);}
            ctx.restore();
        },
    });
}

function visibility(node) {
    const count = Number(value(node,"character_count",2));
    for (const widget of node.widgets ?? []) {
        const match = /^character(\d+)(?:_.*)?$/.exec(widget.name);
        if (!match) continue;
        const id = Number(match[1]);
        const box = value(node,`character${id}_geometry`,"point")==="box";
        const hide = id>count || (!box && /_(width|height)$/.test(widget.name)) ||
            (/_lora_(?:clip_)?strength$/.test(widget.name) && value(node,`character${id}_lora`,"None")==="None");
        if(hide && !widget.rsMcSaved && !widget.type?.startsWith("converted-widget")) {
            widget.rsMcSaved={type:widget.type,computeSize:widget.computeSize,hidden:widget.hidden};
            widget.type="rs-mc-hidden";widget.hidden=true;widget.computeSize=()=>[0,-4];
        } else if(!hide && widget.rsMcSaved) {Object.assign(widget,widget.rsMcSaved);delete widget.rsMcSaved;}
    }
    if(typeOf(node)==="RSMultiCharacterPrompt") {
        // Remove only unused sockets. Connected out-of-count rows stay visible
        // and serialized, but the backend excludes them from the final pipe.
        for(let i=(node.inputs?.length??0)-1;i>=0;i--) {
            const input=node.inputs[i], match=/^character(\d+)(_text)?$/.exec(input.name);
            if(!match) continue;
            const id=Number(match[1]);
            const active=id<=count && (!match[2] || value(node,`character${id}_kind`,"character")==="text");
            if(!active && input.link==null) node.removeInput(i);
        }
        for(let id=1;id<=count;id++) {
            for(const name of [`character${id}`,...(value(node,`character${id}_kind`,"character")==="text"?[`character${id}_text`]:[])]) {
                if(!node.inputs?.some(i=>i.name===name)) node.addInput(name,"STRING");
            }
        }
    }
    const size=node.computeSize();node.setSize([Math.max(340,node.size[0],size[0]),size[1]]);node.setDirtyCanvas(true,true);
}

app.registerExtension({
    name:"RS.MultiCharacter.Builder",
    async beforeRegisterNodeDef(nodeType,nodeData) {
        if(!roles.has(nodeData.name) && nodeData.name!==finalType) return;
        const created=nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated=function(){
            const result=created?.apply(this,arguments);
            if(nodeData.name==="RSMultiCharacterPosition" || nodeData.name===finalType) addDiagram(this);
            for(const widget of this.widgets ?? []) {
                const callback=widget.callback;
                widget.callback=(...args)=>{callback?.apply(widget,args);visibility(this);};
            }
            visibility(this);return result;
        };
        const configured=nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure=function(){const result=configured?.apply(this,arguments);visibility(this);return result;};
    },
});
