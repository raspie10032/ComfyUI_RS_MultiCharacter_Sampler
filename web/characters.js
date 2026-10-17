import { app } from "../../scripts/app.js";

const colors = ["#ff8d91", "#81bcff", "#94dd9d", "#ffd27f", "#c3a0ff", "#7fe5df", "#f5a6d8", "#cedd78", "#c7b6a2", "#e0e5ed"];
function addPreview(node) {
    node.addCustomWidget?.({
        name: "rs_mc_layout_preview", type: "rs_mc_display", serialize: false,
        options: { serialize: false }, serializeValue: () => undefined,
        computeSize: () => [240, 218],
        draw(ctx, node, width, y) {
            const value = name => node.widgets?.find(w => w.name === name)?.value;
            const count = Number(value("character_count") ?? 5);
            const mode = value("layout_mode") ?? "points";
            const side = Math.min(width - 32, 180), left = (width - side) / 2, top = y + 26;
            ctx.save();
            ctx.font = "12px sans-serif"; ctx.fillStyle = "#d1d8e2";
            ctx.fillText("XY 0–1 · " + mode, 14, y + 16);
            ctx.fillStyle = "#191f28"; ctx.fillRect(left, top, side, side);
            ctx.strokeStyle = "#67758a"; ctx.strokeRect(left, top, side, side);
            for (let i = 1; i <= count; i++) {
                if (mode === "points" && value(`character${i}_kind`) === "text") continue;
                const text = mode !== "points" && value(`character${i}_kind`) === "text";
                const boxes = mode === "boxes" || (mode === "mixed" && (text || value(`character${i}_geometry`) === "box"));
                if (value(`character${i}_enable`) === false || !String(value(`character${i}${text ? '_text' : ''}`) ?? "").trim()) continue;
                const x = Number(value(`character${i}_x`) ?? .5), cy = Number(value(`character${i}_y`) ?? .5);
                if (!Number.isFinite(x) || !Number.isFinite(cy)) continue;
                const w = Number(value(`character${i}_width`) ?? .4), h = Number(value(`character${i}_height`) ?? .8);
                const invalid = boxes && (x-w/2 < 0 || cy-h/2 < 0 || x+w/2 > 1 || cy+h/2 > 1);
                const color = invalid ? "#ff4b4b" : colors[i-1];
                ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = 1.5;
                if (boxes) {
                    ctx.globalAlpha = .15; ctx.fillRect(left+(x-w/2)*side, top+(cy-h/2)*side, w*side, h*side);
                    ctx.globalAlpha = 1; ctx.strokeRect(left+(x-w/2)*side, top+(cy-h/2)*side, w*side, h*side);
                }
                ctx.beginPath(); ctx.arc(left+x*side, top+cy*side, 3, 0, Math.PI*2); ctx.fill();
                ctx.fillText(text ? `${i}: ${String(value(`character${i}_text`)).slice(0, 16)}` : String(i), left+x*side+6, top+cy*side-5);
            }
            ctx.restore();
        },
    });
}

// Keep widgets in their original order so saved workflows retain every value.
function updateSlots(node) {
    const count = Number(node.widgets?.find(w => w.name === "character_count")?.value ?? 5);
    const value = name => node.widgets?.find(w => w.name === name)?.value;
    const mode = value("layout_mode") ?? "points";
    for (const widget of node.widgets ?? []) {
        const match = /^character(\d+)(?:_.*)?$/.exec(widget.name);
        const preview = widget.name === "rs_mc_layout_preview";
        if (!match && !preview) continue;
        const text = match && mode !== "points" && value(`character${match[1]}_kind`) === "text";
        const boxes = mode === "boxes" || (mode === "mixed" && match && (text || value(`character${match[1]}_geometry`) === "box"));
        const hide = preview ? mode === "points" : Number(match[1]) > count ||
            (!boxes && /_(width|height)$/.test(widget.name)) ||
            (mode === "points" && /_kind$/.test(widget.name)) ||
            (/_text$/.test(widget.name) && !text) ||
            (/_geometry$/.test(widget.name) && (mode !== "mixed" || text)) ||
            (/_lora(?:_.*)?$/.test(widget.name) && text) ||
            (/_lora_(?:clip_)?strength$/.test(widget.name) &&
                (value(`character${match[1]}_lora`) ?? "None") === "None");
        if (hide && !widget.rsMcVisibleState && !widget.type?.startsWith("converted-widget")) {
            widget.rsMcVisibleState = { type: widget.type, computeSize: widget.computeSize, hidden: widget.hidden };
            widget.type = "rs-mc-hidden";
            widget.hidden = true;
            widget.computeSize = () => [0, -4];
            if (widget.inputEl) widget.inputEl.hidden = true;
        } else if (!hide && widget.rsMcVisibleState) {
            if (widget.type === "rs-mc-hidden") {
                Object.assign(widget, widget.rsMcVisibleState);
                if (widget.inputEl) widget.inputEl.hidden = false;
            }
            delete widget.rsMcVisibleState;
        }
    }
    const needed = node.computeSize();
    node.setSize([Math.max(node.size[0], needed[0]), needed[1]]);
    node.setDirtyCanvas(true, true);
}

app.registerExtension({
    name: "RS.MultiCharacter.Characters",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (!["RSMultiCharacterPrompts"].includes(nodeData.name)) return;
        const onCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onCreated?.apply(this, arguments);
            addPreview(this);
            for (const control of this.widgets?.filter(w => ["character_count", "layout_mode"].includes(w.name) || /^character\d+_(kind|geometry|lora)$/.test(w.name)) ?? []) {
                const callback = control.callback;
                control.callback = (...args) => {
                    callback?.apply(control, args);
                    updateSlots(this);
                };
            }
            updateSlots(this);
            return result;
        };
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = onConfigure?.apply(this, arguments);
            updateSlots(this);
            return result;
        };
    },
});
