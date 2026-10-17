const fs = require('fs'), vm = require('vm'), assert = require('node:assert/strict');
let extension;
vm.runInNewContext(fs.readFileSync('web/characters.js', 'utf8').replace(/^import [^\r\n]*\r?\n/, ''), {
    app: { registerExtension(e) { extension = e; } },
});
class Node {
    constructor() {
        this.widgets = [{name:'character_count', value:2}, {name:'layout_mode', value:'points'}];
        for(let i=1;i<=10;i++) for(const [suffix,value] of Object.entries({enable:true, prompt:`char${i}`, x:.5, y:.5, width:.4, height:.8, kind:'character', text:'', geometry:'point', lora:'None', lora_strength:.8, lora_clip_strength:1.}))
            this.widgets.push({name:`character${i}${suffix==='prompt'?'':'_'+suffix}`, value, type:'number', computeSize:()=>[200,20]});
        this.size=[400,100];
    }
    addCustomWidget(w){this.widgets.push(w);}
    computeSize(){return [400,100];}
    setSize(v){this.size=v;}
    setDirtyCanvas(){}
}
(async()=>{
    await extension.beforeRegisterNodeDef(Node,{name:'RSMultiCharacterPrompts'});
    const n=new Node(), old=n.widgets.map(w=>w.name); n.onNodeCreated();
    const w=name=>n.widgets.find(w=>w.name===name), preview=w('rs_mc_layout_preview');
    assert.equal(w('character1_width').hidden,true); assert.equal(preview.hidden,true);
    w('layout_mode').value='boxes'; w('layout_mode').callback();
    assert.equal(w('character1_width').type,'number'); assert.equal(w('character3_width').hidden,true);
    assert.equal(preview.type,'rs_mc_display'); assert.equal(preview.serializeValue(),undefined);
    const labels=[];
    const ctx=new Proxy({}, {get:(_,k)=>k==='fillText'?(s)=>labels.push(s):()=>{},set:()=>true});
    preview.draw(ctx,n,400,20); assert(labels.includes('1')&&labels.includes('2')); assert(!labels.includes('3'));
    assert.equal(w('character1_lora_strength').hidden,true);
    w('character1_lora').value='character-a.safetensors'; w('character1_lora').callback();
    assert.notEqual(w('character1_lora_strength').hidden,true);
    assert.notEqual(w('character1_lora_clip_strength').hidden,true);
    assert.equal(w('character3_lora').hidden,true);
    assert.equal(w('character2_text').hidden,true);
    w('character2_kind').value='text'; w('character2_text').value='HELLO'; w('character2_kind').callback();
    assert.equal(w('character2_text').type,'number');
    assert.equal(w('character2_lora').hidden,true);
    preview.draw(ctx,n,400,20); assert(labels.includes('2: HELLO'));
    w('layout_mode').value='mixed'; w('layout_mode').callback();
    assert.equal(w('character1_width').hidden,true);
    assert.equal(w('character1_geometry').type,'number');
    assert.equal(w('character2_geometry').hidden,true);
    assert.equal(w('character2_width').type,'number');
    w('character1_geometry').value='box'; w('character1_geometry').callback();
    assert.equal(w('character1_width').type,'number');
    w('character_count').value=1; n.onConfigure(); assert.equal(w('character2_width').hidden,true);
    assert.deepEqual(n.widgets.slice(0,old.length).map(w=>w.name),old);
    w('layout_mode').value='points'; w('layout_mode').callback(); assert.equal(preview.hidden,true);
    assert.equal(w('character1_width').value,.4);
    console.log('Box controls, active slots, preview draw, nonserialization and legacy order passed');
})();
