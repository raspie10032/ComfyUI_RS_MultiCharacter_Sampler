// SPDX-License-Identifier: GPL-3.0-only
const vm=require('vm'),assert=require('node:assert/strict');
const load=require('./ui_source.cjs');
(async()=>{
  for(const order of [['interaction','node_help'],['node_help','interaction']]) {
    const extensions=[];
    const app={registerExtension(e){extensions.push(e);},extensionManager:{setting:{get(){return 'en';}}}};
    for(const file of order) vm.runInNewContext(load(`web/${file}.js`).replace(/^import[^\n]*\n/gm,'').replaceAll('export function','function'),{app});
    class Node {
      constructor(){this.type='RSMultiCharacterInteraction';this.size=[340,300];this.inputs=[];
        this.widgets=Object.entries({preset:'baseline',delay_steps:17,decrement:.37}).map(([name,value])=>({name,value,type:'combo',options:{},computeSize:()=>[300,20],inputEl:{hidden:false},callback(...args){this.args=args;return 42;}}));}
      addCustomWidget(w){this.widgets.push(w);}
      computeSize(){return [340,100+this.widgets.reduce((n,w)=>n+(w.computeSize?.(340)[1]??20),0)];}
      setSize(size){this.size=size;this.onResize?.();}
      setDirtyCanvas(){}
    }
    for(const extension of extensions) await extension.beforeRegisterNodeDef(Node,{name:'RSMultiCharacterInteraction'});
    const node=new Node(),get=name=>node.widgets.find(w=>w.name===name);
    const choose=value=>{get('preset').value=value;return get('preset').callback('event');};
    node.onNodeCreated();
    const before=node.widgets.filter(w=>w.serialize!==false).map(w=>[w.name,w.value]);
    for(const preset of ['baseline','delay3','delay6']){
      assert.equal(choose(preset),42);assert.deepEqual(get('preset').args,['event']);
      assert.equal(get('delay_steps').hidden,true);assert.equal(get('decrement').hidden,true);
      assert.equal(get('rs_mc_node_help').type,'rs_mc_display');
    }
    choose('custom');
    for(const name of ['delay_steps','decrement']) {assert.notEqual(get(name).hidden,true);assert.equal(get(name).type,'combo');assert.equal(get(name).inputEl.hidden,false);}
    choose('baseline');
    node.inputs=[{name:'preset',link:9}];node.onConnectionsChange();
    assert.notEqual(get('delay_steps').hidden,true);
    node.inputs=[];node.onConnectionsChange();assert.equal(get('delay_steps').hidden,true);
    choose('custom');get('decrement').type='converted-widget';get('decrement').hidden=true;
    choose('baseline');choose('custom');assert.equal(get('decrement').type,'converted-widget');assert.equal(get('decrement').hidden,true);
    node.onConfigure();node.onNodeCreated();
    choose('baseline');
    assert.deepEqual(node.widgets.filter(w=>w.serialize!==false).map(w=>[w.name,w.value]),before);
    assert.equal(node.widgets.filter(w=>w.name==='rs_mc_node_help').length,1);
    assert.equal(get('rs_mc_node_help').serializeValue(),undefined);
  }
  console.log('Interaction preset controls: folding, linked preset, converted sockets, values, callbacks and extension order passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
