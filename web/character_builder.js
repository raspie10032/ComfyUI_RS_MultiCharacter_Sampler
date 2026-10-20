import { app } from "../../scripts/app.js";
import { maskPreview, rememberMaskPreview, placedSupport } from "./mask_preview.js";
import { drawingSupports } from "./mask_drawing.js";
import { addPositionEditor } from "./position_editor.js";

const roles = new Set(["RSMultiCharacterPrompt", "RSMultiCharacterLoRA", "RSMultiCharacterPosition", "RSMultiCharacterMask", "RSMultiCharacterMaskDraw"]);
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
        if (type === "RSMultiCharacterMaskDraw") {
            const masks = drawingSupports(item);
            for (let id = 1; id <= 10; id++) {
                const slot = slots.get(id) ?? {id, enabled:true, kind:"character", geometry:"point", x:.5, y:.5, width:.4, height:.8};
                slot.masked = masks.has(id);
                slot.maskSupport = masks.get(id) ?? null;
                slots.set(id, slot);
            }
            if (inputNode(item, "drawing") || inputNode(item, "margin")) unknown = true;
            lastCount = Math.max(lastCount, ...masks.keys());
            continue;
        }
        if (type === "RSMultiCharacterMask") {
            const id = Number(value(item, "character_id", 1));
            const slot = slots.get(id) ?? {id, enabled:true, kind:"character", geometry:"point", x:.5, y:.5, width:.4, height:.8};
            slot.masked = !!value(item, "enabled", true);
            slot.maskSupport = slot.masked ? maskPreview(item) : null;
            if (inputNode(item, "character_id") || inputNode(item, "enabled")) unknown = true;
            slots.set(id, slot);
            lastCount = Math.max(lastCount, id);
            continue;
        }
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
                try { slot.maskTransform = id <= count ? JSON.parse(value(item, "mask_transforms", "{}"))[id] ?? [0,0,1] : [0,0,1]; }
                catch { unknown = true; slot.maskTransform = [0,0,1]; }
                if (inputNode(item, "mask_transforms")) unknown = true;
            }
            slots.set(id,slot);
        }
    }
    for (const slot of slots.values()) if (slot.masked && slot.maskSupport) {
        slot.maskOriginal = slot.maskSupport;
        slot.maskSupport = placedSupport(slot.maskOriginal, slot.maskTransform);
    }
    return {slots:[...slots.values()].filter(s=>s.id<=(promptCount??lastCount) && s.enabled),unknown};
}

export function centersFor(slots) {
    const centers = slots.map(s => s.masked && s.maskSupport ? s.maskSupport.center : [Number(s.x), Number(s.y)]);
    const points = slots.map((s,i) => s.geometry === "point" && !s.masked ? i : -1).filter(i => i >= 0);
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
    if (lang.startsWith("ko")) return ["예상 배치 · XY 0–1", "번호별 설정 · 최종 구도 보장 아님", "연결값 확인 필요: 생성 시 좌표 결정", "프롬프트 연결 대기: ", "마스크 표시 · 캔버스 밖은 자동 잘림", "마스크 연결·실행 필요: "];
    if (lang.startsWith("ja")) return ["配置の目安 · XY 0–1", "番号別設定 · 最終構図の保証ではありません", "接続値の確認が必要です", "プロンプト未接続: ", "マスク表示 · キャンバス外は切り取り", "マスク接続・実行が必要: "];
    return ["Layout guide · XY 0–1", "By number · composition is approximate", "Linked values: layout resolved at execution", "Prompt connection missing: ", "Mask guide · overflow is clipped", "Connect/run mask nodes: "];
}

export function loraModeHelp(node) {
    const lang = app.extensionManager?.setting?.get?.("Comfy.Locale") ?? globalThis.navigator?.language ?? "en";
    const normal = value(node, "lora_application_mode", "precision") === "normal";
    if (lang.startsWith("ko")) return normal ? [
        "일반 적용 · 빠른 계산 공유",
        "Anima·SDXL의 지원되는 선형 LoRA는 레이어 계산을 공유합니다. 정밀 모드와 세부 결과가 달라질 수 있습니다.",
        "미지원 모델·LoRA는 정밀 방식으로 처리하며 생성 정보에 이유를 표시합니다.",
        "모든 캐릭터 슬롯에 적용합니다. 디테일러는 두 모드 모두 한 캐릭터씩 정밀 방식으로 보정합니다.",
    ] : [
        "정밀 적용 · 캐릭터별 독립 계산",
        "캐릭터의 LoRA 설정마다 모델 예측을 분리합니다. 지원되는 LoRA는 작은 행렬 최적화를 사용합니다.",
        "서로 다른 LoRA 설정이 많으면 일반 모드보다 느립니다. 더 좋은 그림이나 완전한 특징 분리를 보장하지 않습니다.",
        "기존 워크플로의 기본 방식입니다. 모든 캐릭터 슬롯에 적용하며 디테일러도 이 방식으로 보정합니다.",
    ];
    if (lang.startsWith("ja")) return normal ? [
        "通常適用 · 高速なレイヤー共有",
        "対応するAnima・SDXLの線形LoRAはレイヤー計算を共有します。精密モードとは細部が変わる場合があります。",
        "未対応のモデル・LoRAは精密方式で処理し、生成情報に理由を表示します。",
        "全スロットに適用します。Detailerは両モードとも1人ずつ精密方式で補正します。",
    ] : [
        "精密適用 · キャラクター別の独立計算",
        "LoRA設定ごとにモデル予測を分離します。対応LoRAには低ランク行列の最適化を使います。",
        "異なるLoRA設定が多いほど通常モードより遅くなります。画質向上や完全な特徴分離は保証しません。",
        "既存ワークフローの既定方式です。全スロットに適用し、Detailerもこの方式で補正します。",
    ];
    return normal ? [
        "Normal · Fast layer sharing",
        "Supported Anima/SDXL linear LoRAs share layer calculations. Details can differ from Precision.",
        "Unsupported models/adapters use Precision and report the reason in generation info.",
        "Applies to every character slot. Detailer corrects one character at a time using Precision in both modes.",
    ] : [
        "Precision · Independent character predictions",
        "Each LoRA setting gets separate model predictions. Supported LoRAs use low-rank optimization.",
        "More distinct LoRA settings take longer than Normal. This does not guarantee better artwork or complete separation.",
        "Compatibility default for existing workflows. Applies to every character slot; Detailer uses this method too.",
    ];
}

function helpLines(node, width) {
    const limit = Math.max(240, width - 32), lines = [];
    for (const text of loraModeHelp(node)) {
        let line = "", used = 0;
        for (const token of text.match(/[A-Za-z0-9][A-Za-z0-9/'·.-]*|\s+|[^\s]/gu) ?? []) {
            const size = [...token].reduce((sum, ch) => sum + (/[\u1100-\uffff]/.test(ch) ? 12 : 7), 0);
            if (line && used + size > limit) { lines.push(line.trimEnd()); line = ""; used = 0; }
            if (!line && !token.trim()) continue;
            line += token; used += size;
        }
        if (line) lines.push(line);
        lines.push("");
    }
    return lines;
}

function addLoraModeHelp(node) {
    node.addCustomWidget({
        name: "rs_mc_lora_mode_help", type: "rs_mc_display", serialize: false,
        options: { serialize: false }, serializeValue: () => undefined,
        computeSize: (width = node.size?.[0] ?? 340) => [300, helpLines(node, width).length * 17 + 16],
        draw(ctx, node, width, y) {
            const lines = helpLines(node, width);
            ctx.save();
            ctx.fillStyle = "#171d27"; ctx.fillRect(8, y + 2, width - 16, lines.length * 17 + 10);
            ctx.font = "12px sans-serif";
            lines.forEach((line, i) => {
                ctx.fillStyle = i === 0 ? "#d1e3ff" : "#b4bdcc";
                ctx.fillText(line, 16, y + 19 + i * 17, width - 32);
            });
            ctx.restore();
        },
    });
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
            const points = slots.map((s,i) => s.geometry === "point" && !s.masked ? i : -1).filter(i => i>=0);
            // Schematic partitions. Box coverage overrides point coverage, as in sampling.
            if (!dynamic) for (let row=0; row<32; row++) for (let col=0; col<48; col++) {
                const x=(col+.5)/48, cy=(row+.5)/32;
                let ids=slots.map((s,i) => {
                    if (s.masked) {
                        const m = s.maskSupport;
                        return m && m.data[Math.min(m.height-1,Math.floor(cy*m.height))*m.width+Math.min(m.width-1,Math.floor(x*m.width))] ? i : -1;
                    }
                    return s.geometry === "box" && Math.abs(x-s.x)<=s.width/2 && Math.abs(cy-s.y)<=s.height/2 ? i : -1;
                }).filter(i=>i>=0);
                if (!ids.length && points.length) ids=[points.reduce((a,b)=>Math.hypot(x-centers[a][0],cy-centers[a][1])<=Math.hypot(x-centers[b][0],cy-centers[b][1])?a:b)];
                for (const i of ids) {
                    ctx.fillStyle=colors[(slots[i].id-1)%10]; ctx.globalAlpha=.22/ids.length;
                    ctx.fillRect(left+col*w/48,top+row*h/32,w/48+.5,h/32+.5);
                }
            }
            ctx.globalAlpha=1; ctx.strokeStyle="#66768f"; ctx.strokeRect(left,top,w,h);
            if (!dynamic) slots.forEach((s,i)=>{
                if (s.masked && (!s.maskSupport || s.maskSupport.empty)) return;
                const [x,cy]=centers[i], box=s.geometry==="box" && !s.masked;
                const invalid=box && (x-s.width/2<0 || x+s.width/2>1 || cy-s.height/2<0 || cy+s.height/2>1);
                ctx.strokeStyle=ctx.fillStyle=invalid?"#ff4b4b":colors[(s.id-1)%10];
                if (box) ctx.strokeRect(left+(x-s.width/2)*w,top+(cy-s.height/2)*h,s.width*w,s.height*h);
                ctx.beginPath();ctx.arc(left+x*w,top+cy*h,3,0,Math.PI*2);ctx.fill();
                ctx.fillText(`${s.id}${s.kind==="text"?" T":s.masked?" M":""}`,Math.min(left+x*w+6,left+w-24),Math.max(top+12,top+cy*h-6));
            });
            const pending=slots.filter(s=>s.masked && (!s.maskSupport || s.maskSupport.empty)).map(s=>s.id);
            ctx.fillStyle="#b4bdcc";ctx.fillText(dynamic?text[2]:pending.length?text[5]+pending.join(", "):slots.some(s=>s.masked)?text[4]:text[1],left,top+h+18,width-32);
            const missing=slots.filter(s=>!s.promptConnected).map(s=>s.id);
            if(missing.length) {ctx.fillStyle="#ffd27f";ctx.fillText(text[3]+missing.join(", "),left,top+h+36,width-32);}
            ctx.restore();
        },
    });
}

function migrateTextInputs(node) {
    // Old saved graphs may have both style and literal-text sockets. Move the
    // literal-text connection to the shared socket once the graph is restored.
    for (let i=(node.inputs?.length??0)-1;i>=0;i--) {
        const input=node.inputs[i], match=/^(character\d+)_text$/.exec(input.name);
        if (!match) continue;
        if (input.link!=null) {
            const links=node.graph?.links;
            const link=links?.get?.(input.link) ?? links?.[input.link];
            if (!link) continue;
            if (value(node,`${match[1]}_kind`,"character")==="text") {
                let target=node.inputs.findIndex(v=>v.name===match[1]);
                if (target<0) {node.addInput(match[1],"STRING");target=node.inputs.length-1;}
                const source=node.graph.getNodeById(link.origin_id);
                if (!source) continue;
                source.connect(link.origin_slot,node,target);
            }
        }
        node.removeInput(i);
    }
}

function visibility(node, updateSockets = true) {
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
    if(updateSockets && typeOf(node)==="RSMultiCharacterPrompt") {
        migrateTextInputs(node);
        // Remove only unused sockets. Connected out-of-count rows stay visible
        // and serialized, but the backend excludes them from the final pipe.
        for(let i=(node.inputs?.length??0)-1;i>=0;i--) {
            const input=node.inputs[i], match=/^character(\d+)$/.exec(input.name);
            if(!match) continue;
            const id=Number(match[1]);
            const active=id<=count;
            if(!active && input.link==null) node.removeInput(i);
        }
        for(let id=1;id<=count;id++) {
            const name=`character${id}`;
            if(!node.inputs?.some(i=>i.name===name)) node.addInput(name,"STRING");
        }
    }
    const size=node.computeSize();node.setSize([Math.max(340,node.size[0],size[0]),size[1]]);node.setDirtyCanvas(true,true);
}

app.registerExtension({
    name:"RS.MultiCharacter.Builder",
    async beforeRegisterNodeDef(nodeType,nodeData) {
        if(nodeData.name === "RSMultiCharacterMaskDraw" || (!roles.has(nodeData.name) && nodeData.name!==finalType)) return;
        const created=nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated=function(){
            const result=created?.apply(this,arguments);
            if(nodeData.name==="RSMultiCharacterPosition" && this.addDOMWidget) addPositionEditor(this, { collectSlots, centersFor, colors });
            else if(nodeData.name==="RSMultiCharacterPosition" || nodeData.name===finalType || nodeData.name==="RSMultiCharacterMask") addDiagram(this);
            if(nodeData.name==="RSMultiCharacterLoRA") addLoraModeHelp(this);
            for(const widget of this.widgets ?? []) {
                const callback=widget.callback;
                widget.callback=(...args)=>{callback?.apply(widget,args);visibility(this);};
            }
            visibility(this);return result;
        };
        if (nodeData.name === "RSMultiCharacterMask") {
            const executed = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(message) {
                const result = executed?.apply(this, arguments);
                rememberMaskPreview(this, message);
                this.setDirtyCanvas(true, true);
                return result;
            };
        }
        const configured=nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure=function(){
            const result=configured?.apply(this,arguments);
            visibility(this,false);
            // Configure may also be used when pasting nodes. Wait for links to
            // be restored before migrating the old two-input layout.
            queueMicrotask(()=>visibility(this));
            return result;
        };
        const graphConfigured=nodeType.prototype.onGraphConfigured;
        nodeType.prototype.onGraphConfigured=function(){const result=graphConfigured?.apply(this,arguments);visibility(this);return result;};
    },
});
