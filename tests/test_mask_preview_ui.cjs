const fs = require('fs'), vm = require('vm'), assert = require('node:assert/strict');
const src = fs.readFileSync('web/mask_preview.js','utf8').replace(/^import[^\n]*\n/gm,'').replaceAll('export function','function');
const sandbox = {app:{},api:{apiURL:s=>s},URLSearchParams};
vm.runInNewContext(src,sandbox);
const {transformSupport,maskPreview,rememberMaskPreview,maskState} = sandbox;
const data = new Float32Array(80*120);
for (let y=20;y<60;y++) for (let x=40;x<80;x++) data[y*120+x]=1;
const source={width:120,height:80,data};
function rectangle(mask,x0,y0,x1,y1){
 for(let y=0;y<80;y++) for(let x=0;x<120;x++) assert.equal(mask.data[y*120+x],x>=x0&&x<x1&&y>=y0&&y<y1?1:0);
}
rectangle(transformSupport(source,0,0,.5),50,30,70,50);
rectangle(transformSupport(source,.25,0,2),50,0,120,80);
rectangle(transformSupport(source,.5,-.5,1),100,0,120,20);
rectangle(transformSupport(source,0,0,.5,.5,2),48,28,72,52);
assert.equal(transformSupport(source,1,0,1).empty,true);
const upstream={id:1,type:'InvertMask',widgets:[{name:'amount',value:1}],inputs:[]};
const node={id:2,type:'RSMultiCharacterMask',widgets:[{name:'scale',value:1}],inputs:[{name:'mask'}],getInputNode(i){return i===0?upstream:null;}};
assert.equal(maskPreview(node),null);
rememberMaskPreview(node,{images:[{filename:'test.png',type:'temp'}]});
const state=node.rsMaskExecuted.state;
assert.equal(state,JSON.stringify(maskState(node)));
upstream.widgets[0].value=2;
assert.notEqual(state,JSON.stringify(maskState(node)));
assert.equal(maskPreview(node),null);
rememberMaskPreview(node,{images:[]});assert.equal(node.rsMaskExecuted,null);
// Cycles and long arbitrary processing graphs cannot hang the guide.
upstream.inputs=[{}];upstream.getInputNode=()=>node;
assert.doesNotThrow(()=>JSON.stringify(maskState(node)));
console.log('Mask guide: uniform scaling, shifts, clipping, dilation, stale-input invalidation and cycles passed');
