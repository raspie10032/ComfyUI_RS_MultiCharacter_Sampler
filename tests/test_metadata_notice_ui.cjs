const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const pending = [];
let extension;
const sandbox = {
    app: {registerExtension(value) { extension = value; }},
    api: {fetchApi(url) { return new Promise(resolve => pending.push({url, resolve})); }},
    encodeURIComponent,
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('web/metadata_notice.js', 'utf8').replace(/^import[^\n]*\n/gm,''), sandbox);
(async () => {
    class Node {
        constructor() { this.widgets=[{name:'image',value:'22 people.png'}]; this.size=[340,100]; }
        computeSize() { return [340,120]; }
        setSize(size) { this.size=size; }
        setDirtyCanvas() {}
    }
    await extension.beforeRegisterNodeDef(Node,{name:'RSMultiCharacterLoadImage'});
    const node=new Node(); node.onNodeCreated();
    assert.match(pending[0].url,/22%20people.png/);
    node.widgets[0].value='2.png'; node.widgets[0].callback();
    pending[1].resolve({ok:true,json:async()=>({character_count:2,truncated:false})});
    await new Promise(setImmediate);
    pending[0].resolve({ok:true,json:async()=>({character_count:22,truncated:true})});
    await new Promise(setImmediate);
    assert.equal(node._rsMetadataNotice,null,'stale notice must not replace current selection');
    node.widgets[0].value='22.png'; node.onConfigure();
    pending[2].resolve({ok:true,json:async()=>({character_count:22,local_count:10,truncated:true})});
    await new Promise(setImmediate);
    assert.equal(node._rsMetadataNotice.character_count,22);
    node.widgets[0].value='bad.png'; node.widgets[0].callback();
    pending[3].resolve({ok:false}); await new Promise(setImmediate);
    assert.equal(node._rsMetadataNotice,null);
    node.onConfigure(); node.onRemoved();
    pending[4].resolve({ok:true,json:async()=>({character_count:22,truncated:true})});
    await new Promise(setImmediate);
    assert.equal(node._rsMetadataNotice,null);
    console.log('Metadata notices: selection, stale replies, invalid files, configure and removal passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
