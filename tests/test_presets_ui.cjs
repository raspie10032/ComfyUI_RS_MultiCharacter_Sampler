const fs = require('fs'), vm = require('vm'), assert = require('node:assert/strict');
const presets = JSON.parse(fs.readFileSync('web/model_presets.json', 'utf8'));
let extension, lang = 'en';
vm.runInNewContext(fs.readFileSync('web/presets.js', 'utf8')
    .replace(/^import [^\r\n]*\r?\n/gm, '').replaceAll('import.meta.url', '"http://localhost/presets.js"'), {
    URL, console,
    fetch: async () => ({ok:true, json:async () => presets}),
    app: { registerExtension(e) { extension = e; }, ui: {settings:{getSettingValue:()=>lang}} },
    ComfyWidgets: { STRING(node, name) { const w = node.addWidget('text',name,'',null); w.inputEl={}; return {widget:w}; } },
});
class Node {
    constructor() {
        this.widgets=[]; this.properties={}; this.inputs=[]; this.changes=0;
        this.graph={beforeChange:()=>this.changes++, afterChange:()=>this.changes++};
        for(const [name,value] of Object.entries({...presets[0].settings,seed:123,width:1536,height:768,prompt:'my prompt',negative_prompt:'bad',prompt_syntax:'NovelAI',autosave:false,use_image_settings:false,layout_method:'regional'}))
            this.addWidget(typeof value==='number'?'number':'combo', name, value, ()=>{});
        this.w('sampler_name').options.values=['euler_ancestral','euler'];
        this.w('scheduler').options.values=['sgm_uniform','normal','simple'];
    }
    w(name){return this.widgets.find(w=>w.name===name);}
    addWidget(type,name,value,callback,options={}){const w={type,name,value,callback,options}; this.widgets.push(w); return w;}
    setDirtyCanvas(){}
    choose(id){const p=presets.find(p=>p.id===id);this.w('rs_mc_preset').callback(p.label[lang]);}
    apply(){this.w('rs_mc_apply_preset').callback();}
    values(){return Object.fromEntries(this.widgets.filter(w=>!w.name.startsWith('rs_mc_')).map(w=>[w.name,w.value]));}
}
(async()=>{
    await extension.beforeRegisterNodeDef(Node,{name:'RSMultiCharacterSampler'});
    const a=new Node(), original=a.values(), order=a.widgets.map(w=>w.name); a.onNodeCreated();
    const other=new Node();other.onNodeCreated();
    a.choose('moss_8step'); assert.deepEqual(a.values(),original,'selection alone must not mutate controls');
    a.apply(); assert.equal(a.w('steps').value,8);assert.equal(a.w('cfg').value,3);assert.equal(a.w('scheduler').value,'simple');
    assert.match(a.w('rs_mc_preset_info').value,/match/);assert.match(a.w('rs_mc_preset_info').value,/0.7/);
    for(const key of ['seed','width','height','prompt','negative_prompt','prompt_syntax','autosave','layout_method']) assert.equal(a.w(key).value,original[key],key);
    assert.deepEqual(other.values(),original,'other sampler nodes must be independent');
    a.w('cfg').value=2.5; a.w('cfg').callback(2.5); assert.match(a.w('rs_mc_preset_info').value,/manual/);
    a.onConfigure();assert.equal(a.w('cfg').value,2.5,'workflow load must not apply preset');
    a.onConnectionsChange();assert.equal(a.w('cfg').value,2.5);
    for(const p of presets){a.choose(p.id);a.apply();for(const [k,v] of Object.entries(p.settings))assert.equal(a.w(k).value,v);}
    // Full preflight: incompatible hosts, external links and restore/native paths must never partially edit settings.
    a.choose('krea2');
    a.w('use_image_settings').value=true;let before=a.values();a.apply();assert.deepEqual(a.values(),before);assert.match(a.w('rs_mc_preset_info').value,/Turn off/);
    a.w('use_image_settings').value=false;a.w('layout_method').value='moss_native';before=a.values();a.apply();assert.deepEqual(a.values(),before);assert.match(a.w('rs_mc_preset_info').value,/regional/);
    a.w('layout_method').value='regional';
    for(const key of ['steps','scheduler','use_image_settings','layout_method']){
        a.inputs=[{name:key,link:7}];before=a.values();a.apply();assert.deepEqual(a.values(),before);assert.match(a.w('rs_mc_preset_info').value,/Disconnect/);
    }
    a.inputs=[];a.w('steps').type='converted-widget';before=a.values();a.apply();assert.deepEqual(a.values(),before);a.w('steps').type='number';
    a.w('scheduler').options.values=['normal'];before=a.values();a.apply();assert.deepEqual(a.values(),before);assert.match(a.w('rs_mc_preset_info').value,/Unavailable/);
    a.w('scheduler').options.values=['simple','normal','sgm_uniform'];
    a.w('steps').options.min=20;before=a.values();a.apply();assert.deepEqual(a.values(),before);delete a.w('steps').options.min;
    // No positional schema change; status and selectors are UI-only, stable IDs live in graph properties.
    assert.deepEqual(a.widgets.slice(0,order.length).map(w=>w.name),order);
    assert.equal(a.properties.rs_mc_preset,'krea2');
    for(const w of a.widgets.slice(order.length)){assert.equal(w.options.serialize,false);assert.equal(w.serializeValue(),undefined);}
    for(const [language,label] of [['en','Apply preset'],['ko','프리셋 적용'],['ja','プリセットを適用']]){
        lang=language;a.onConfigure();assert.equal(a.w('rs_mc_apply_preset').label,label);a.choose('sd15_mixed');a.apply();assert.equal(a.w('cfg').value,7);
    }
    a.properties.rs_mc_preset='unknown-future-preset';before=a.values();a.onConfigure();a.apply();assert.deepEqual(a.values(),before);
    // The shipped presets must reproduce their published examples, including old widget ordering.
    const ordered=['prompt','negative_prompt','width','height','seed','control_after_generate','steps','cfg','sampler_name','scheduler','autosave','save_format','webp_quality','prompt_syntax','use_image_settings','region_feather','initial_common_prior','common_after_step3_boost','initial_character_gain','initial_spatial_separation','boundary_hold_steps','boundary_decrement','layout_method'];
    for(const p of presets){
        const source=JSON.parse(fs.readFileSync(p.source));
        const values=source.nodes.find(n=>n.type==='RSMultiCharacterSampler').widgets_values;
        for(const [k,v] of Object.entries(p.settings))assert.equal(v,values[ordered.indexOf(k)],`${p.id} / ${k}`);
    }
    console.log(`${presets.length} presets: explicit apply, manual edits/reload, isolation, atomic conflict guards, locales, schema stability, and published examples passed`);
})().catch(e=>{console.error(e);process.exitCode=1;});
