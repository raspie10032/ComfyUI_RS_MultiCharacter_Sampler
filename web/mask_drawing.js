// SPDX-License-Identifier: GPL-3.0-only
import { chineseLocale, chineseText } from "./i18n.js";
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { transformSupport } from "./mask_preview.js";

const colors = ["#ff8d91", "#81bcff", "#94dd9d", "#ffd27f", "#c3a0ff", "#7fe5df", "#f5a6d8", "#cedd78", "#c7b6a2", "#e0e5ed"];
const cache = new WeakMap();
const val = (node, name, fallback) => node.widgets?.find(w => w.name === name)?.value ?? fallback;
const empty = () => ({ version: 1, width: 768, height: 1024, layers: {} });
const layerAt = (data, id) => data.layers[id] ??= { strokes: [], x: 0, y: 0, scale: 1 };
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const lang = () => String(app.extensionManager?.setting?.get?.("Comfy.Locale") ?? navigator.language ?? "en");
const text = (en, ko, ja) => chineseLocale(lang()) ? chineseText(en, lang()) : lang().startsWith("ko") ? ko : lang().startsWith("ja") ? ja : en;

export function parseDrawing(value) {
    const data = JSON.parse(value);
    if (data?.version !== 1 || !Number.isInteger(data.width) || !Number.isInteger(data.height) ||
        data.width < 64 || data.height < 64 || data.width > 2048 || data.height > 2048 ||
        !data.layers || typeof data.layers !== "object" || Array.isArray(data.layers)) throw Error("Invalid drawing");
    return data;
}

export function drawStrokes(ctx, layer, w, h) {
    ctx.clearRect(0, 0, w, h);
    ctx.lineCap = "round"; ctx.lineJoin = "round";
    for (const stroke of layer.strokes) {
        ctx.globalCompositeOperation = stroke.tool === "erase" ? "destination-out" : "source-over";
        ctx.fillStyle = ctx.strokeStyle = "white";
        const width = Math.max(1, stroke.size * Math.min(w, h));
        ctx.lineWidth = width;
        ctx.beginPath();
        stroke.points.forEach(([x, y], i) => i ? ctx.lineTo(x * w, y * h) : ctx.moveTo(x * w, y * h));
        ctx.stroke();
        // A click is also a stroke, and round caps must survive an eraser pass.
        for (const [x, y] of [stroke.points[0], stroke.points.at(-1)]) {
            ctx.beginPath(); ctx.arc(x * w, y * h, width / 2, 0, Math.PI * 2); ctx.fill();
        }
    }
    ctx.globalCompositeOperation = "source-over";
}

export function rasterSupport(data, layer, margin = 0, maxSide = 256) {
    if (typeof document === "undefined" || !layer.strokes?.length) return null;
    const factor = Math.min(1, maxSide / Math.max(data.width, data.height));
    const width = Math.max(1, Math.round(data.width * factor)), height = Math.max(1, Math.round(data.height * factor));
    const canvas = document.createElement("canvas"); canvas.width = width; canvas.height = height;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    drawStrokes(ctx, layer, width, height);
    const rgba = ctx.getImageData(0, 0, width, height).data;
    const pixels = new Float32Array(width * height);
    for (let i = 0; i < pixels.length; i++) pixels[i] = rgba[i * 4 + 3] / 255;
    return transformSupport({ width, height, data: pixels, sourceWidth: data.width, sourceHeight: data.height },
        layer.x ?? 0, layer.y ?? 0, layer.scale ?? 1, .5, margin);
}

// The same drawing data drives downstream layout guides before execution.
export function drawingSupports(node) {
    const raw = val(node, "drawing", ""), margin = val(node, "margin", 24);
    const previous = cache.get(node);
    if (previous?.raw === raw && previous.margin === margin) return previous.layers;
    let layers = new Map();
    try {
        const data = parseDrawing(raw);
        for (const [id, layer] of Object.entries(data.layers)) {
            const support = rasterSupport(data, layer, margin);
            if (support && !support.empty) layers.set(Number(id), support);
        }
    } catch { /* The backend reports invalid or empty drawing data. */ }
    cache.set(node, { raw, margin, layers });
    return layers;
}

function editor(node) {
    const stored = node.widgets.find(w => w.name === "drawing");
    stored.hidden = true; stored.type = "rs-mc-hidden"; stored.computeSize = () => [0, -4];
    const root = document.createElement("div");
    root.className = "rs-mc-mask-drawing";
    root.style.cssText = "box-sizing:border-box;padding:8px;overflow:auto;background:#202630;color:#eee;font:12px sans-serif;pointer-events:auto;height:100%;";
    for (const event of ["pointerdown", "wheel", "keydown"]) root.addEventListener(event, e => e.stopPropagation());
    const row = () => { const el = document.createElement("div"); el.style.cssText = "display:flex;flex-wrap:wrap;gap:5px;align-items:center;margin-bottom:7px"; root.append(el); return el; };
    const button = (parent, label, fn) => {
        const el = document.createElement("button"); el.textContent = label; el.type = "button"; el.onclick = fn;
        el.style.cssText = "background:#343e4e;color:#eee;border:1px solid #617087;border-radius:4px;padding:4px 7px;cursor:pointer";
        parent.append(el); return el;
    };
    let data = empty(), active = 1, mode = "brush", brush = .06, background = null, bgKey = "", revision = 0;
    let drag = null, undo = [], lastValue, pending = false;
    const toolbar = row();
    const picker = document.createElement("input"); picker.type = "file"; picker.accept = "image/*"; picker.hidden = true; root.append(picker);
    button(toolbar, text("Reference image", "참조 이미지 열기", "参照画像"), () => picker.click());
    button(toolbar, text("Hide reference", "참조 이미지 끄기", "参照画像を外す"), () => {
        remember(); delete data.background; background = null; bgKey = ""; save();
    });
    button(toolbar, text("Undo", "되돌리기", "元に戻す"), () => {
        finish(); if (!undo.length) return; data = JSON.parse(undo.pop()); save(); sync();
    });
    button(toolbar, text("Clear layer", "선택 영역 지우기", "選択領域を消す"), () => {
        remember(); delete data.layers[active]; save(); sync();
    });
    const slots = row(), slotButtons = [];
    for (let i = 1; i <= 10; i++) slotButtons.push(button(slots, String(i), () => { finish(); active = i; sync(); }));
    const tools = row();
    const modes = [
        button(tools, text("Paint", "그리기", "描く"), () => { mode = "brush"; sync(); }),
        button(tools, text("Erase", "지우개", "消しゴム"), () => { mode = "erase"; sync(); }),
        button(tools, text("Move", "이동", "移動"), () => { mode = "move"; sync(); }),
    ];
    const brushLabel = document.createElement("label"); brushLabel.textContent = text("Brush ", "붓 크기 ", "ブラシ "); tools.append(brushLabel);
    const brushControl = document.createElement("input"); brushControl.type = "range"; brushControl.min = 1; brushControl.max = 200; brushControl.value = 60;
    brushControl.style.width = "90px"; brushLabel.append(brushControl);
    brushControl.oninput = () => { brush = Number(brushControl.value) / 1000; };
    const transforms = row();
    const controls = {};
    for (const [key, label, min, max, step] of [["x", "X", -1, 1, .01], ["y", "Y", -1, 1, .01], ["scale", text("Size ×", "크기 ×", "倍率 ×"), .05, 4, .05]]) {
        const labelEl = document.createElement("label"); labelEl.textContent = label + " "; transforms.append(labelEl);
        const el = document.createElement("input"); el.type = "number"; el.min = min; el.max = max; el.step = step; el.style.width = "65px"; labelEl.append(el);
        el.title = text("Selected layer only; overflow is clipped.", "선택한 번호만 조절하며 캔버스 밖은 잘립니다.", "選択番号のみ調整し、外側は切り取ります。");
        el.onchange = () => { if (!Number.isFinite(el.valueAsNumber)) return sync(); remember(); layerAt(data, active)[key] = clamp(el.valueAsNumber, min, max); save(); sync(); };
        controls[key] = el;
    }
    const canvas = document.createElement("canvas"); canvas.setAttribute("aria-label", text("Character mask drawing", "캐릭터 마스크 그리기", "キャラクターマスク描画"));
    canvas.style.cssText = "display:block;max-width:100%;max-height:400px;margin:auto;background:#111820;touch-action:none;cursor:crosshair";
    root.append(canvas);
    const status = document.createElement("div"); status.style.cssText = "margin-top:8px;line-height:1.5;white-space:pre-wrap"; root.append(status);
    const note = document.createElement("div"); note.style.cssText = "margin-top:5px;color:#b6c1d1;line-height:1.5";
    note.textContent = text("Select a character number, then paint its region. Reference only; masks guide placement, not exact pose. Blank layers use XY/boxes. Canvas overflow is clipped.",
        "번호 선택 → 해당 캐릭터 영역을 칠하세요. 이미지는 참조용이며 자세를 고정하지 않습니다. 빈 번호는 XY·박스를 사용하며 캔버스 밖 마스크는 잘립니다.",
        "番号を選び領域を塗ります。画像は参照のみでポーズ固定ではありません。空の番号はXY・ボックスを使い、外側は切り取ります。"); root.append(note);

    function remember() {
        undo.push(JSON.stringify(data));
        while (undo.length > 16 || (undo.length > 1 && undo.reduce((s, v) => s + v.length, 0) > 4 * 1024 * 1024)) undo.shift();
    }
    function save() {
        const serialized = JSON.stringify(data);
        if (serialized.length > 4 * 1024 * 1024) { status.textContent = text("Too many strokes: undo and simplify.", "획이 너무 많습니다. 되돌린 뒤 단순하게 그려 주세요.", "線が多すぎます。元に戻して簡略化してください。"); return; }
        stored.value = lastValue = serialized; stored.callback?.(serialized); cache.delete(node);
        node.setDirtyCanvas(true, true); schedule();
    }
    function reference() {
        const descriptor = data.background, key = JSON.stringify(descriptor ?? null);
        if (key === bgKey) return;
        bgKey = key; background = null;
        const current = ++revision;
        if (!descriptor?.filename) return;
        const image = new Image();
        image.onload = () => { if (current !== revision) return; background = image; schedule(); };
        image.onerror = () => { if (current === revision) status.textContent = text("Reference missing; painted masks are still saved.", "참조 이미지가 없습니다. 그린 마스크는 그대로 보존됩니다.", "参照画像がありません。描いたマスクは保持されています。"); };
        image.src = api.apiURL(`/view?${new URLSearchParams(descriptor)}`);
    }
    function sync() {
        const layer = data.layers[active];
        for (let i = 1; i <= 10; i++) {
            slotButtons[i - 1].style.borderColor = colors[i - 1];
            slotButtons[i - 1].style.background = active === i ? colors[i - 1] : "#343e4e";
            slotButtons[i - 1].style.color = active === i ? "#111820" : "#eee";
            slotButtons[i - 1].textContent = `${i}${data.layers[i]?.strokes.length ? " ●" : ""}`;
        }
        for (const key of ["x", "y", "scale"]) controls[key].value = layer?.[key] ?? (key === "scale" ? 1 : 0);
        modes.forEach((el, i) => el.style.borderColor = ["brush", "erase", "move"][i] === mode ? "#fff" : "#617087");
        reference(); schedule();
    }
    function render() {
        pending = false;
        const ratio = Math.min(1, 512 / Math.max(data.width, data.height));
        canvas.width = Math.round(data.width * ratio); canvas.height = Math.round(data.height * ratio);
        const ctx = canvas.getContext("2d"), w = canvas.width, h = canvas.height;
        if (background) { ctx.globalAlpha = .65; ctx.drawImage(background, 0, 0, w, h); ctx.globalAlpha = 1; }
        for (const [id, layer] of Object.entries(data.layers)) {
            const mask = rasterSupport(data, layer, val(node, "margin", 24), 384);
            if (!mask) continue;
            const tinted = document.createElement("canvas"); tinted.width = mask.width; tinted.height = mask.height;
            const tc = tinted.getContext("2d"), pixels = tc.createImageData(mask.width, mask.height);
            const color = colors[Number(id) - 1], rgb = [1, 3, 5].map(pos => parseInt(color.slice(pos, pos + 2), 16));
            for (let i = 0; i < mask.data.length; i++) if (mask.data[i]) pixels.data.set([...rgb, Number(id) === active ? 140 : 85], i * 4);
            tc.putImageData(pixels, 0, 0); ctx.drawImage(tinted, 0, 0, w, h);
            if (!mask.empty) {
                const [x, y] = mask.center;
                ctx.fillStyle = "#101721"; ctx.fillRect(x * w - 10, y * h - 11, 22, 22);
                ctx.fillStyle = color; ctx.font = "bold 16px sans-serif"; ctx.fillText(id, x * w - 5, y * h + 6);
            }
        }
        status.textContent = text(`Character ${active} · ${data.width}×${data.height} · colored regions include margin`,
            `캐릭터 ${active}번 · ${data.width}×${data.height} · 색 영역에 여유 폭 포함`,
            `キャラクター${active} · ${data.width}×${data.height} · 色領域は余白込み`);
    }
    function schedule() { if (!pending) { pending = true; requestAnimationFrame(render); } }
    function point(e) {
        const rect = canvas.getBoundingClientRect();
        return [clamp((e.clientX - rect.left) / rect.width, -4, 5), clamp((e.clientY - rect.top) / rect.height, -4, 5)];
    }
    function sourcePoint(p, layer) { const s = layer.scale ?? 1; return p.map((v, i) => clamp((v - .5 - (i ? layer.y ?? 0 : layer.x ?? 0)) / s + .5, -4, 5)); }
    canvas.onpointerdown = e => {
        if (e.button !== 0) return; e.preventDefault(); canvas.setPointerCapture(e.pointerId); remember();
        const layer = layerAt(data, active), p = point(e);
        drag = { id: e.pointerId, layer, start: p, x: layer.x ?? 0, y: layer.y ?? 0, tool: mode };
        if (mode !== "move") {
            if (layer.strokes.length >= 2000) { drag = null; return; }
            drag.stroke = { tool: mode, size: brush, points: [sourcePoint(p, layer)] }; layer.strokes.push(drag.stroke);
        }
        schedule();
    };
    canvas.onpointermove = e => {
        if (!drag || drag.id !== e.pointerId) return;
        const p = point(e);
        if (drag.tool === "move") {
            drag.layer.x = clamp(drag.x + p[0] - drag.start[0], -1, 1);
            drag.layer.y = clamp(drag.y + p[1] - drag.start[1], -1, 1);
        } else {
            const next = sourcePoint(p, drag.layer), prev = drag.stroke.points.at(-1);
            if (Math.hypot(next[0] - prev[0], next[1] - prev[1]) < .001) return;
            drag.stroke.points.push(next);
        }
        schedule();
    };
    function finish() { if (!drag) return; drag = null; save(); sync(); }
    canvas.onpointerup = canvas.onpointercancel = canvas.onlostpointercapture = finish;
    picker.onchange = async () => {
        const file = picker.files?.[0]; if (!file) return;
        status.textContent = text("Loading reference…", "참조 이미지 불러오는 중…", "参照画像を読込中…");
        try {
            const form = new FormData(); form.append("image", file); form.append("subfolder", "RS_MaskDrawing"); form.append("type", "input");
            const response = await api.fetchApi("/upload/image", { method: "POST", body: form });
            if (!response.ok) throw Error(`HTTP ${response.status}`);
            const uploaded = await response.json(), descriptor = { filename: uploaded.name, subfolder: uploaded.subfolder ?? "", type: uploaded.type ?? "input" };
            const image = new Image();
            await new Promise((resolve, reject) => { image.onload = resolve; image.onerror = reject; image.src = api.apiURL(`/view?${new URLSearchParams(descriptor)}`); });
            remember(); data.background = descriptor;
            const factor = Math.min(1, 2048 / Math.max(image.naturalWidth, image.naturalHeight));
            data.width = Math.max(64, Math.round(image.naturalWidth * factor)); data.height = Math.max(64, Math.round(image.naturalHeight * factor));
            save(); sync();
        } catch (error) { status.textContent = text("Reference load failed: ", "참조 이미지 로드 실패: ", "参照画像の読込失敗: ") + String(error); }
        picker.value = "";
    };
    function restore() {
        try { data = parseDrawing(stored.value); lastValue = stored.value; undo = []; sync(); }
        catch { status.textContent = text("Invalid drawing data. Restore a valid workflow.", "드로잉 데이터가 올바르지 않습니다. 저장된 워크플로를 확인해 주세요.", "描画データを確認してください。"); }
    }
    const dom = node.addDOMWidget("rs_mc_mask_editor", "rs_mc_display", root, { serialize: false, getValue: () => undefined, setValue: () => {} });
    dom.serialize = false; dom.computeSize = () => [480, 680];
    const previous = stored.callback;
    stored.callback = function (...args) { previous?.apply(this, args); if (stored.value !== lastValue) restore(); };
    const marginWidget = node.widgets.find(w => w.name === "margin");
    const marginChanged = marginWidget?.callback;
    if (marginWidget) marginWidget.callback = function (...args) { marginChanged?.apply(this, args); schedule(); };
    node.rsMaskDrawingRestore = restore;
    restore();
    node.setSize([Math.max(500, node.size[0]), Math.max(node.computeSize()[1], 740)]);
}

app.registerExtension({
    name: "RS.MultiCharacter.MaskDrawing",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "RSMultiCharacterMaskDraw") return;
        const created = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () { const result = created?.apply(this, arguments); editor(this); return result; };
        const configured = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () { const result = configured?.apply(this, arguments); this.rsMaskDrawingRestore?.(); return result; };
    },
});
