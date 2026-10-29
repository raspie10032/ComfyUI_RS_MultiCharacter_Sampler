// SPDX-License-Identifier: GPL-3.0-only
// Kept numerically in sync with pose3d.py (cross-language geometry tests).
export const JOINTS = {
    pelvis: [null,[0,.94,0]], chest:['pelvis',[0,.36,0]], neck:['chest',[0,.20,0]], head:['neck',[0,.16,0]],
    right_shoulder:['chest',[-.23,.04,0]], right_elbow:['right_shoulder',[0,-.29,0]], right_wrist:['right_elbow',[0,-.26,0]],
    left_shoulder:['chest',[.23,.04,0]], left_elbow:['left_shoulder',[0,-.29,0]], left_wrist:['left_elbow',[0,-.26,0]],
    right_hip:['pelvis',[-.115,-.035,0]], right_knee:['right_hip',[0,-.42,0]], right_ankle:['right_knee',[0,-.40,0]],
    left_hip:['pelvis',[.115,-.035,0]], left_knee:['left_hip',[0,-.42,0]], left_ankle:['left_knee',[0,-.40,0]],
};
export const LIMBS=[['right_shoulder','right_elbow',.075],['right_elbow','right_wrist',.06],['left_shoulder','left_elbow',.075],['left_elbow','left_wrist',.06],['right_hip','right_knee',.10],['right_knee','right_ankle',.075],['left_hip','left_knee',.10],['left_knee','left_ankle',.075]];
export const add=(a,b)=>a.map((v,i)=>v+b[i]);
export const sub=(a,b)=>a.map((v,i)=>v-b[i]);
export const mul=(a,s)=>a.map(v=>v*s);
export const dot=(a,b)=>a.reduce((v,x,i)=>v+x*b[i],0);
export const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const norm=a=>mul(a,1/Math.hypot(...a));
export const mv=(m,v)=>m.map(row=>dot(row,v));
export const mm=(a,b)=>a.map(row=>[0,1,2].map(j=>row.reduce((s,v,k)=>s+v*b[k][j],0)));
export function rotation(angles){
    const [x,y,z]=angles.map(v=>v*Math.PI/180),[a,b,c,d,e,f]=[Math.cos(x),Math.sin(x),Math.cos(y),Math.sin(y),Math.cos(z),Math.sin(z)];
    return [[c*e,-c*f,d],[a*f+b*d*e,a*e-b*d*f,-b*c],[b*f-a*d*e,b*e+a*d*f,a*c]];
}
export function defaultScene(){return {version:1,width:768,height:1024,mask_mode:'full',camera:{position:[0,1.15,4.1],target:[0,.9,0],fov:38},people:[-.4,.4].map((x,i)=>({id:i+1,position:[x,0,0],rotation:[0,0,0],scale:1,bulk:1,joints:{}}))};}
export function skeleton(person){
    const frames={},points={},root=rotation(person.rotation);
    for(const [name,[parent,offset]] of Object.entries(JOINTS)){
        const r=parent?frames[parent]:root,base=parent?points[parent]:person.position;
        points[name]=add(base,mv(r,mul(offset,person.scale)));
        frames[name]=mm(r,rotation(person.joints[name]??[0,0,0]));
    }
    return {points,frames};
}
const SPHERE=[],FACES=[];
for(let y=0;y<=8;y++)for(let x=0;x<=12;x++)SPHERE.push([Math.sin(Math.PI*y/8)*Math.cos(2*Math.PI*x/12),Math.cos(Math.PI*y/8),Math.sin(Math.PI*y/8)*Math.sin(2*Math.PI*x/12)]);
for(let y=0;y<8;y++)for(let x=0;x<12;x++){const a=y*13+x;FACES.push([a,a+13,a+1],[a+1,a+13,a+14]);}
export function mannequin(person){
    const {points:p,frames:r}=skeleton(person),vertices=[],faces=[],size=person.scale,bulk=person.bulk;
    const ellipsoid=(center,radius,frame)=>{
        const offset=vertices.length;
        for(const v of SPHERE)vertices.push(add(center,mv(frame,v.map((n,i)=>n*radius[i]*size))));
        for(const f of FACES)faces.push(f.map(i=>i+offset));
    };
    ellipsoid(p.pelvis,[.22*bulk,.15,.14*bulk],r.pelvis);
    ellipsoid(mul(add(p.pelvis,p.neck),.5),[.25*bulk,.31,.14*bulk],r.chest);
    ellipsoid(p.neck,[.065,.10,.065],r.neck);
    ellipsoid(add(p.head,mv(r.head,[0,.025*size,.025*size])),[.125,.175,.13],r.head);
    for(const [a,b,radius] of LIMBS)ellipsoid(mul(add(p[a],p[b]),.5),[radius*bulk,Math.hypot(...sub(p[b],p[a]))/size/2+radius*.45,radius*bulk],r[a]);
    for(const side of ['right','left']){
        const wrist=side+'_wrist',ankle=side+'_ankle';
        ellipsoid(add(p[wrist],mv(r[wrist],[0,-.065*size,0])),[.055*bulk,.09,.035],r[wrist]);
        ellipsoid(add(p[ankle],mv(r[ankle],[0,-.025*size,.07*size])),[.065*bulk,.06,.14],r[ankle]);
    }
    return {vertices,faces,points:p};
}
export function project(vertices,camera,width,height){
    const forward=norm(sub(camera.target,camera.position)),right=norm(cross(forward,[0,1,0])),up=cross(right,forward),f=height/(2*Math.tan(camera.fov*Math.PI/360));
    return vertices.map(v=>{const local=mv([right,up,forward],sub(v,camera.position)),z=Math.abs(local[2])<1e-10?1e-10:local[2];return [width/2+local[0]*f/z,height/2-local[1]*f/z,local[2]];});
}
