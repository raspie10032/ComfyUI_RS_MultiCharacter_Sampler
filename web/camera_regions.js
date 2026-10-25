// SPDX-License-Identifier: GPL-3.0-only
// Diagram-only camera output. Sampling keeps using camera_layout.py and full masks.
import { projectLayout, randomCamera } from "./camera_control.js";

const warped = new WeakMap();
const value = (node, name, fallback) => node.widgets?.find(w => w.name === name)?.value ?? fallback;
const linked = (node, name) => node.inputs?.some(i => i.name === name && i.link != null);

function matrix(v) {
    const s = 2 ** (2 * (.5 - v.distance)), a = v.roll * Math.PI / 180;
    const co = Math.cos(a), si = Math.sin(a), aspect = v.canvas_aspect;
    const yaw = v.azimuth * Math.PI / 180, pitch = v.elevation * Math.PI / 180;
    const ca = Math.cos(yaw), sa = Math.sin(yaw), ce = Math.cos(pitch), se = Math.sin(pitch);
    const perspective = v.layout_sync === "perspective";
    if (perspective && Math.abs(ca * ce) < 1e-6) return null;
    const focal = 2 * Math.hypot(aspect, 1) / s;
    const g = perspective ? -sa * ce * aspect / focal : 0, h = perspective ? se / focal : 0;
    const i = 1 - .5 * (g + h);
    const ux = perspective ? co * ca - si * sa * se : co;
    const uy = perspective ? -si * ce : -si;
    const vx = perspective ? si * ca + co * sa * se : si;
    const vy = perspective ? co * ce : co;
    return [.5*g+s*ux, .5*h+s*uy/aspect, .5*i-.5*s*(ux+uy/aspect),
        .5*g+s*vx*aspect, .5*h+s*vy, .5*i-.5*s*(vx*aspect+vy), g, h, i];
}

function inverse(m) {
    const [a,b,c,d,e,f,g,h,i] = m;
    const adj = [e*i-f*h,c*h-b*i,b*f-c*e,f*g-d*i,a*i-c*g,c*d-a*f,d*h-e*g,b*g-a*h,a*e-b*d];
    const det = a*adj[0] + b*adj[3] + c*adj[6];
    return adj.map(v => v / det);
}

export function cameraSupport(source, m) {
    let cache = warped.get(source);
    if (!cache) { cache = new Map(); warped.set(source, cache); }
    const key = JSON.stringify(m);
    if (cache.has(key)) return cache.get(key);
    const [a,b,c,d,e,f,g,h,i] = inverse(m), {width, height} = source;
    const data = new Uint8Array(width * height);
    let count = 0, cx = 0, cy = 0;
    for (let row = 0; row < height; row++) for (let col = 0; col < width; col++) {
        const x = (col+.5)/width, y = (row+.5)/height, depth = g*x+h*y+i;
        if (Math.abs(depth) <= 1e-12) continue;
        const px = (a*x+b*y+c)/depth, py = (d*x+e*y+f)/depth;
        if (px < 0 || px >= 1 || py < 0 || py >= 1) continue;
        if (source.data[Math.floor(py*height)*width+Math.floor(px*width)]) {
            data[row*width+col] = 1; count++; cx += x; cy += y;
        }
    }
    const result = {width, height, data, center: count ? [cx/count,cy/count] : [.5,.5], empty: !count};
    if (cache.size >= 4) cache.delete(cache.keys().next().value);
    cache.set(key, result);
    return result;
}

export function cameraSlots(node, slots) {
    if (!slots.length || node.mode === 4) return {slots, unknown:false};
    if (node.mode === 2 || slots.some(s=>s.dynamic)) return {slots,unknown:true};
    const v = Object.fromEntries(Object.entries({enabled:true,strength:1.2,layout_sync:"fixed",
        azimuth:0,elevation:0,distance:.5,roll:0,canvas_aspect:1,random_mode:"off",random_seed:0})
        .map(([k,d]) => [k,value(node,k,d)]));
    if (["enabled","strength","layout_sync"].some(k => linked(node,k))) return {slots,unknown:true};
    if (!v.enabled || !v.strength || v.layout_sync === "fixed") return {slots,unknown:false};
    if (["canvas_aspect","random_mode"].some(k => linked(node,k))) return {slots,unknown:true};
    const random = v.random_mode !== "off";
    if (!["off","balanced","full"].includes(v.random_mode) || (random &&
        (!Number.isInteger(v.random_seed) || v.random_seed < 0 || v.random_seed > 0xffffffff))) return {slots,unknown:true};
    if ((random ? ["random_seed"] : ["distance","roll",...(v.layout_sync === "perspective" ? ["azimuth","elevation"] : [])])
        .some(k => linked(node,k))) return {slots,unknown:true};
    if (random) Object.assign(v, randomCamera(v.random_mode, v.random_seed));
    if (![v.azimuth,v.elevation,v.distance,v.roll,v.canvas_aspect].every(Number.isFinite) ||
        v.canvas_aspect < .1 || v.canvas_aspect > 10 || !["distance_and_roll","perspective"].includes(v.layout_sync)) return {slots,unknown:true};
    const m = matrix(v);
    if (!m) return {slots,unknown:true};
    let unknown = false;
    const point = (x,y) => projectLayout(x,y,v.distance,v.roll,v.canvas_aspect,v.azimuth,v.elevation,v.layout_sync === "perspective");
    const result = slots.map(slot => {
        if (slot.kind === "text") return slot; // Native text regions are screen-fixed.
        if (slot.masked) {
            if (!slot.maskSupport) { unknown = true; return slot; }
            // Preserve the identity raster, as the backend does.
            const identity = v.distance === .5 && v.roll === 0 &&
                (v.layout_sync !== "perspective" || (v.azimuth === 0 && v.elevation === 0));
            const support = identity ? slot.maskSupport : cameraSupport(slot.maskSupport,m);
            unknown ||= support.empty;
            return {...slot,maskSupport:support,x:support.center[0],y:support.center[1]};
        }
        if (slot.geometry === "box") {
            const corners = [-1,1].flatMap(dx => [-1,1].map(dy => point(slot.x+dx*slot.width/2,slot.y+dy*slot.height/2)));
            const left = Math.max(0,Math.min(...corners.map(p=>p[0]))), right = Math.min(1,Math.max(...corners.map(p=>p[0])));
            const top = Math.max(0,Math.min(...corners.map(p=>p[1]))), bottom = Math.min(1,Math.max(...corners.map(p=>p[1])));
            unknown ||= left >= right || top >= bottom;
            return {...slot,x:(left+right)/2,y:(top+bottom)/2,width:right-left,height:bottom-top};
        }
        const [x,y] = point(slot.x,slot.y);
        unknown ||= x < 0 || x > 1 || y < 0 || y > 1;
        return {...slot,x,y};
    });
    return {slots:result,unknown};
}
