// SPDX-License-Identifier: GPL-3.0-only
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Small, bounded, diagram-only rasters. Sampling always uses the original MASK.
const sources = new Map(), previews = new WeakMap();
const placements = new WeakMap();

export function placedSupport(source, transform) {
    const [dx, dy, scale] = transform ?? [0, 0, 1];
    if (dx === 0 && dy === 0 && scale === 1) return source;
    let cache = placements.get(source);
    if (!cache) { cache = new Map(); placements.set(source, cache); }
    const key = JSON.stringify([dx, dy, scale]);
    if (!cache.has(key)) {
        if (cache.size >= 4) cache.delete(cache.keys().next().value);
        cache.set(key, transformSupport(source, dx, dy, scale, .5, 0, source.center));
    }
    return cache.get(key);
}
const value = (node, name, fallback) => node.widgets?.find(w => w.name === name)?.value ?? fallback;
const typeOf = node => node.comfyClass ?? node.type;
const input = (node, name) => node.getInputNode?.(node.inputs?.findIndex(i => i.name === name) ?? -1);

export function transformSupport(source, offsetX = 0, offsetY = 0, scale = 1, threshold = .5, margin = 0, pivot = [.5, .5]) {
    const { width: w, height: h, data } = source;
    let result = new Uint8Array(w * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
        const sx = Math.floor((x + .5 - pivot[0] * w - offsetX * w) / scale + pivot[0] * w);
        const sy = Math.floor((y + .5 - pivot[1] * h - offsetY * h) / scale + pivot[1] * h);
        result[y * w + x] = sx >= 0 && sx < w && sy >= 0 && sy < h && data[sy * w + sx] > threshold ? 1 : 0;
    }
    // Dilation follows the transform, matching prepare_mask. Prefix sums bound
    // the cost even for a large margin on a tiny source image.
    const rx = Math.round(margin * w / (source.sourceWidth ?? w));
    const ry = Math.round(margin * h / (source.sourceHeight ?? h));
    for (const [horizontal, radius] of [[true, rx], [false, ry]]) {
        if (!radius) continue;
        const next = new Uint8Array(w * h), length = horizontal ? w : h;
        const lines = horizontal ? h : w;
        for (let line = 0; line < lines; line++) {
            const sums = new Uint32Array(length + 1);
            const index = n => horizontal ? line * w + n : n * w + line;
            for (let n = 0; n < length; n++) sums[n + 1] = sums[n] + result[index(n)];
            for (let n = 0; n < length; n++) next[index(n)] = sums[Math.min(length, n + radius + 1)] > sums[Math.max(0, n - radius)] ? 1 : 0;
        }
        result = next;
    }
    let count = 0, cx = 0, cy = 0;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (result[y * w + x]) {
        count++; cx += (x + .5) / w; cy += (y + .5) / h;
    }
    return { width: w, height: h, data: result, center: count ? [cx / count, cy / count] : [.5, .5], empty: !count };
}

function loadSource(key, descriptor, channel) {
    if (sources.has(key)) return sources.get(key);
    const entry = { raster: null };
    // Do not retain an unbounded collection of source images across graph edits.
    if (sources.size >= 24) sources.delete(sources.keys().next().value);
    sources.set(key, entry);
    if (typeof Image === "undefined") return entry;
    const image = new Image();
    image.onload = () => {
        try {
            const factor = Math.min(1, 256 / Math.max(image.naturalWidth, image.naturalHeight));
            const width = Math.max(1, Math.round(image.naturalWidth * factor));
            const height = Math.max(1, Math.round(image.naturalHeight * factor));
            const canvas = document.createElement("canvas");
            canvas.width = width; canvas.height = height;
            const ctx = canvas.getContext("2d", { willReadFrequently: true });
            ctx.drawImage(image, 0, 0, width, height);
            const rgba = ctx.getImageData(0, 0, width, height).data;
            const data = new Float32Array(width * height);
            const index = { red: 0, green: 1, blue: 2, alpha: 3 }[channel] ?? 0;
            for (let i = 0; i < data.length; i++) data[i] = channel === "alpha" ? 1 - rgba[i * 4 + 3] / 255 : rgba[i * 4 + index] / 255;
            entry.raster = { width, height, data, sourceWidth: image.naturalWidth, sourceHeight: image.naturalHeight };
        } catch { entry.error = true; }
        app.graph?.setDirtyCanvas(true, true);
    };
    image.onerror = () => { entry.error = true; app.graph?.setDirtyCanvas(true, true); };
    image.src = api.apiURL(`/view?${new URLSearchParams(descriptor)}`);
    return entry;
}

// Changes upstream invalidate an executed preview rather than showing stale
// masks from arbitrary processing nodes as if they were the current result.
export function maskState(node, seen = new Set()) {
    if (!node || seen.has(node) || seen.size >= 64) return null;
    seen.add(node);
    return [node.id, typeOf(node), node.mode, node.widgets?.filter(w => w.serialize !== false).map(w => [w.name, w.value]),
        node.inputs?.map((_, i) => maskState(node.getInputNode?.(i), seen))];
}

export function rememberMaskPreview(node, message) {
    node.rsMaskExecuted = message?.images?.length ? { state: JSON.stringify(maskState(node)), descriptor: message.images[0] } : null;
    previews.delete(node);
}

export function maskPreview(node) {
    if (!value(node, "enabled", true)) return null;
    // Converted widgets are evaluated by ComfyUI. An executed preview is the
    // authoritative fallback for those values and arbitrary MASK providers.
    const linked = ["offset_x", "offset_y", "scale", "threshold", "margin"].some(name => input(node, name));
    let sourceNode = input(node, "mask");
    const seen = new Set();
    while (typeOf(sourceNode ?? {}) === "Reroute" && !seen.has(sourceNode)) {
        seen.add(sourceNode); sourceNode = sourceNode.getInputNode?.(0);
    }
    let key, descriptor, channel, transformed = false;
    const executed = node.rsMaskExecuted;
    if (executed?.state === JSON.stringify(maskState(node))) {
        descriptor = executed.descriptor; channel = "red"; transformed = true;
        key = JSON.stringify([descriptor, channel]);
    } else if (!linked && typeOf(sourceNode ?? {}) === "LoadImageMask" && sourceNode.mode !== 4 && !input(sourceNode, "image") && !input(sourceNode, "channel")) {
        let filename = value(sourceNode, "image", "");
        const annotation = /\s*\[(input|output|temp)\]$/.exec(filename);
        if (annotation) filename = filename.slice(0, annotation.index);
        if (!filename) return null;
        channel = value(sourceNode, "channel", "red");
        descriptor = { filename, type: annotation?.[1] ?? "input" };
        key = JSON.stringify([descriptor, channel]);
    } else {
        return null;
    }
    const source = loadSource(key, descriptor, channel).raster;
    if (!source) return null;
    const args = transformed ? [0, 0, 1, .5, 0] : [value(node, "offset_x", 0), value(node, "offset_y", 0), value(node, "scale", 1), value(node, "threshold", .5), value(node, "margin", 24)];
    const state = JSON.stringify([key, args]);
    const previous = previews.get(node);
    if (previous?.state === state && previous.source === source) return previous.raster;
    const raster = transformSupport(source, ...args);
    previews.set(node, { state, source, raster });
    return raster;
}
