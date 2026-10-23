const fs = require('fs'), vm = require('vm'), assert = require('node:assert/strict');
const source = require("./ui_source.cjs")('web/position_editor.js')
    .replace(/^import[^\n]*\n/gm, '').replaceAll('export function', 'function');
const sandbox = { app: {}, api: {}, URLSearchParams };
vm.runInNewContext(source, sandbox);
const { movedBox, resizedBox, supportBounds, maskPlacements } = sandbox;
const plain = value => JSON.parse(JSON.stringify(value));

// Moving a box preserves size and stays within the canvas.
assert.deepEqual(plain(movedBox({x:.5,y:.5,width:.4,height:.6}, 2, -2)), {x:.8,y:.3});
// A centered resize is constrained by the existing center, including near edges.
assert.deepEqual(plain(resizedBox({x:.2,y:.7}, 1, 0)), {width:.4,height:.6000000000000001});
assert.deepEqual(plain(resizedBox({x:.5,y:.5}, .5, .5)), {width:.01,height:.01});

// The resize handle must follow the actual support, not the full source canvas.
const data = new Float32Array(8 * 6);
for (let y=1;y<5;y++) for(let x=2;x<4;x++) data[y*8+x]=1;
assert.deepEqual(plain(supportBounds({width:8,height:6,data})), [.25,1/6,.5,5/6]);
assert.equal(supportBounds({width:8,height:6,data:new Float32Array(48)}), null);
assert.equal(supportBounds({empty:true}), null);

assert.deepEqual(plain(maskPlacements({widgets:[{name:'mask_transforms',value:'{"3":[-0.15,0,1.1]}'}]})), {'3':[-.15,0,1.1]});
assert.deepEqual(plain(maskPlacements({widgets:[{name:'mask_transforms',value:'broken'}]})), {});
assert.deepEqual(plain(maskPlacements({widgets:[]})), {});
console.log('Position editor: bounded moves/resizes, actual-support handles and placement restoration passed');
