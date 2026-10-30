// SPDX-License-Identifier: GPL-3.0-only
// Native MHR skinning; asset attribution and Apache-2.0 terms accompany the file.
import {rotation as bodyRotation,mm,mv,add} from './model.mjs';
let rig,bindInverse,bindLocal,controls;
const identity=()=>[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]];
const matmul=(a,b)=>a.map(row=>[0,1,2,3].map(j=>row.reduce((s,v,k)=>s+v*b[k][j],0)));
const vector=(m,v)=>m.map(row=>row.reduce((s,x,i)=>s+x*v[i],0));
const extrinsic=angles=>bodyRotation(angles.map(v=>-v))[0].map((_,i)=>bodyRotation(angles.map(v=>-v)).map(row=>row[i]));
function quaternion([x,y,z,w]){
    const n=Math.hypot(x,y,z,w);x/=n;y/=n;z/=n;w/=n;
    return [[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)], [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)], [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]];
}
function globals(angles){
    const result=[];
    for(let i=0;i<rig.names.length;i++){
        const m=identity(),r=mm(bindLocal[i],extrinsic(angles[rig.names[i]]??[0,0,0]));
        for(let a=0;a<3;a++){for(let b=0;b<3;b++)m[a][b]=r[a][b];m[a][3]=rig.localTransforms[i].position[a];}
        result.push(rig.parents[i]<0?m:matmul(result[rig.parents[i]],m));
    }
    return result;
}
export function initRig(data){
    rig=data;controls=Object.fromEntries(Object.entries(rig.controls).map(([key,name])=>[key,rig.names.indexOf(name)]));
    bindLocal=rig.localTransforms.map(t=>quaternion(t.quaternion).map(row=>row.map(v=>v*t.scale)));
    bindInverse=globals({}).map(m=>{
        const inv=identity();
        for(let a=0;a<3;a++)for(let b=0;b<3;b++)inv[a][b]=m[b][a];
        for(let a=0;a<3;a++)inv[a][3]=-inv[a].slice(0,3).reduce((s,v,b)=>s+v*m[b][3],0);
        return inv;
    });
    return rig;
}
export function rigControls(){return Object.keys(controls);}
export function preset(name){return structuredClone(rig.presets[name]);}
export function defaultPerson(id=1){return {id,position:[-.4,0,0],rotation:[0,0,0],scale:1,bulk:1,joints:preset('standing')};}
export function defaultRigScene(){return {version:2,outline:true,width:768,height:1024,mask_mode:'full',camera:{position:[0,1.15,4.1],target:[0,.9,0],fov:38},people:[-.4,.4].map((x,i)=>({...defaultPerson(i+1),position:[x,0,0]}))};}
function posed(person){
    const angles=Object.fromEntries(Object.entries(person.joints).map(([key,v])=>[rig.controls[key],v]));
    for(const rule of rig.proceduralRotations)angles[rig.names[rule.bone]]=rule.axes.map(terms=>terms.reduce((s,[j,axis,w])=>s+(angles[rig.names[j]]?.[axis]??0)*w,0));
    return {angles,matrices:globals(angles)};
}
const insideFrame=(point,planes)=>!planes||planes.every(p=>point.reduce((s,v,i)=>s+v*p[i],p[3])>=-1e-10);
export function clipSourceFrame(vertices,faces,points,planes){
    if(!planes)return {vertices,faces,points};
    const output=vertices.slice(),kept=[],crossings=[];
    const distance=vertices.map(v=>planes.map(p=>v.reduce((s,x,i)=>s+x*p[i],p[3])));
    for(const face of faces){
        if(face.every(i=>distance[i].every(d=>d>=-1e-10))){kept.push(face);continue;}
        if(planes.some((_,p)=>face.every(i=>distance[i][p]<-1e-10)))continue;
        let polygon=face.map(i=>vertices[i]);
        for(const plane of planes){
            const clipped=[];
            for(let i=0;i<polygon.length;i++){
                const a=polygon[i],b=polygon[(i+1)%polygon.length];
                const da=a.reduce((s,v,k)=>s+v*plane[k],plane[3]),db=b.reduce((s,v,k)=>s+v*plane[k],plane[3]);
                if(da>=-1e-10)clipped.push(a);
                if((da>=-1e-10)!==(db>=-1e-10))clipped.push(a.map((v,k)=>v+(b[k]-v)*da/(da-db)));
            }
            polygon=clipped;if(polygon.length<3)break;
        }
        if(polygon.length<3)continue;
        const start=output.length;output.push(...polygon);
        for(let i=1;i<polygon.length-1;i++)crossings.push([start,start+i,start+i+1]);
    }
    kept.push(...crossings);
    const used=[...new Set(kept.flat())].sort((a,b)=>a-b),remap=new Map(used.map((v,i)=>[v,i]));
    return {vertices:used.map(i=>output[i]),faces:kept.map(f=>f.map(i=>remap.get(i))),
        points:Object.fromEntries(Object.entries(points).filter(([,p])=>insideFrame(p,planes)))};
}
export function rigSkeleton(person){
    const {matrices:m}=posed(person),points={},frames={},baseFrames={},r=bodyRotation(person.rotation),size=[person.bulk*person.scale,person.scale,person.bulk*person.scale];
    for(const [key,i] of Object.entries(controls)){
        points[key]=add(mv(r,[0,1,2].map(a=>m[i][a][3]*size[a])),person.position);
        const rot=m[i].slice(0,3).map(row=>row.slice(0,3));
        frames[key]=mm(r,rot);
        // Local manipulator rotation excludes its own delta, retains native bind frame.
        baseFrames[key]=mm(frames[key],extrinsic(person.joints[key]??[0,0,0])[0].map((_,j)=>extrinsic(person.joints[key]??[0,0,0]).map(row=>row[j])));
    }
    const visible=Object.entries(controls).filter(([,i])=>insideFrame(m[i].slice(0,3).map(row=>row[3]),person.source_frame)).map(([key])=>key);
    return {points,frames,baseFrames,visible};
}
export function rigMannequin(person){
    const {matrices}=posed(person),transforms=matrices.map((m,i)=>matmul(m,bindInverse[i]));
    const vertices=[],r=bodyRotation(person.rotation),size=[person.bulk*person.scale,person.scale,person.bulk*person.scale];
    for(let i=0;i<rig.vertices.length/3;i++){
        const v=[...rig.vertices.slice(i*3,i*3+3),1],out=[0,0,0],total=rig.weights.slice(i*4,i*4+4).reduce((a,b)=>a+b,0);
        for(let k=0;k<4;k++){
            const weight=rig.weights[i*4+k]/total;if(!weight)continue;
            const value=vector(transforms[rig.indices[i*4+k]],v);
            for(let j=0;j<3;j++)out[j]+=value[j]*weight;
        }
        vertices.push(out);
    }
    const faces=Array.from({length:rig.faces.length/3},(_,i)=>rig.faces.slice(i*3,i*3+3));
    const localPoints=Object.fromEntries(Object.entries(controls).map(([key,i])=>[key,matrices[i].slice(0,3).map(row=>row[3])]));
    const clipped=clipSourceFrame(vertices,faces,localPoints,person.source_frame);
    const transform=v=>add(mv(r,v.map((v,j)=>v*size[j])),person.position);
    return {vertices:clipped.vertices.map(transform),faces:clipped.faces,
        points:Object.fromEntries(Object.entries(clipped.points).map(([k,v])=>[k,transform(v)]))};
}
