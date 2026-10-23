const fs = require('fs'), vm = require('vm'), assert = require('node:assert/strict');
const extensions = [];
let locale = 'ko', enabled = true, time = 0, nextTimer = 0;
const timers = new Map(), listeners = {};
const clock = {
  setTimer(fn, ms) { const id = ++nextTimer; timers.set(id, {at:time+ms, fn}); return id; },
  clearTimer(id) { timers.delete(id); },
};
function tick(ms) {
  time += ms;
  for (const [id, task] of [...timers]) if (task.at <= time) {timers.delete(id);task.fn();}
}
function element(tag='DIV') {
  const attrs = {}, children = [], classes = new Set();
  return {nodeName:tag, style:{}, children,
    appendChild(e) {children.push(e);e.parentElement=this;},
    remove() {const i=this.parentElement?.children.indexOf(this);if(i>=0)this.parentElement.children.splice(i,1);},
    setAttribute(k,v) {attrs[k]=v;}, getAttribute(k) {return attrs[k];},
    hasAttribute(k) {return k in attrs;}, removeAttribute(k) {delete attrs[k];},
    classList:{add(c){classes.add(c);},remove(c){classes.delete(c);},contains(c){return classes.has(c);}},
    getBoundingClientRect() {return {width:300,height:70};},
    closest() {return null;}, contains(el) {return el===this || children.includes(el);},
    addEventListener() {},
  };
}
const document = {head:element(),body:element(),createElement:element,addEventListener(n,fn){listeners[n]=fn;}};
const window = {setTimeout:clock.setTimer,clearTimeout:clock.clearTimer,innerWidth:1000,innerHeight:700,
  addEventListener(n,fn){listeners[n]=fn;}};
const node={id:1,comfyClass:'RSMultiCharacterPrompt',widgets:[{name:'character_count',value:2}]};
const graph={_nodes:[node],getNodeById(id){return this._nodes.find(n=>String(n.id)===String(id));}};
const canvas=element('CANVAS');
const app={registerExtension(e){extensions.push(e);},graph,
  canvas:{canvas,graph,node_over:node,getWidgetAtCursor(){return this.hit;},hit:node.widgets[0]},
  extensionManager:{setting:{get(name){return name==='Comfy.Locale'?locale:enabled;}}},
};
const sandbox={app,window,document,navigator:{language:'en'}};
vm.createContext(sandbox);
vm.runInContext(require("./ui_source.cjs")('web/widget_tooltips.js')
  .replace(/^import[^\n]*\n/gm,'').replaceAll('export function','function').replaceAll('export const','var'),sandbox);
const {fieldHelp,hoverController,HOVER_DELAY}=sandbox;
assert.equal(HOVER_DELAY,2000);
for(const lang of ['ko','ja','en','zh','zh-TW']) {
  for(const name of ['character1_lora','character10_kind','character10_width','steps','batch_size','initial_common_prior','boundary_decrement','save_format']) {
    const text=fieldHelp('RSMultiCharacterSampler',name,lang);
    assert.ok(text.length>8,`${lang}:${name}`);
    assert.ok(text.length<=200,`${lang}:${name}: too long`);
  }
}
// Every custom control has Chinese help without changing its internal key.
for (const name of vm.runInContext('Object.keys(tips)', sandbox)) {
  for (const lang of ['zh','zh-TW']) {
    assert.match(fieldHelp('RSMultiCharacterSampler',name,lang), /[\u3400-\u9fff]/, `${lang}:${name}`);
  }
}
assert.match(fieldHelp('','character1_width','en'),/fraction/);
assert.match(fieldHelp('','width','en'),/pixels/);
assert.match(fieldHelp('','batch_size','ko'),/캐릭터 수가 아닙니다/);
assert.equal(fieldHelp('','unknown','ko'),'');
assert.equal(fieldHelp('','cfg','fr'),fieldHelp('','cfg','en'));
// Validate every current schema control when a live schema snapshot is supplied.
if(process.env.RS_MC_SCHEMA_PATH) {
  const schemas=JSON.parse(fs.readFileSync(process.env.RS_MC_SCHEMA_PATH,'utf8'));
  let count=0;
  for(const [type,schema] of Object.entries(schemas)) {
    if(!type.startsWith('RSMultiCharacter'))continue;
    for(const group of Object.values(schema.input))for(const [name,spec]of Object.entries(group)) {
      if(!Array.isArray(spec)||spec[1]?.forceInput||!(['STRING','INT','FLOAT','BOOLEAN'].includes(spec[0])||Array.isArray(spec[0])))continue;
      for(const lang of ['en','ko','ja','zh','zh-TW']) assert.ok(fieldHelp(type,name,lang),`${type}.${name}: ${lang}`);
      count++;
    }
  }
  console.log(`Live schema tooltip coverage: ${count} controls in five languages`);
}
let shown=[], hiddenCount=0,valid=true;
const controller=hoverController({...clock,show(t){shown.push(t);},hide(){hiddenCount++;},valid(){return valid;}});
const target={node,widget:node.widgets[0],text:'help',x:1};
controller.move({...target});tick(1999);assert.equal(shown.length,0);
// Moving within the same field must not indefinitely postpone the tooltip.
controller.move({...target,x:5});tick(1);assert.equal(shown.length,1);assert.equal(shown[0].x,5);
controller.clear();controller.move({...target});tick(1500);controller.move(null);tick(1000);assert.equal(shown.length,1);
controller.move({...target});tick(1500);controller.move({...target,widget:{name:'other'}});tick(500);assert.equal(shown.length,1);
tick(1500);assert.equal(shown.length,2);
controller.move({...target});valid=false;tick(2000);assert.equal(shown.length,2);assert.ok(hiddenCount);
controller.clear();assert.equal(timers.size,0);
// Exercise event adapters and native-tooltip suppression, not only timer logic.
const extension=extensions[0];extension.setup();
const move=target=>listeners.mousemove({target,clientX:950,clientY:670,buttons:0});
const visible=()=>document.body.children.find(e=>e.className==='rs-mc-field-tooltip');
canvas.setAttribute('title','Native title');move(canvas);
assert.equal(canvas.hasAttribute('title'),false);assert.ok(document.body.classList.contains('rs-mc-hovering-control'));
tick(1999);assert.equal(visible(),undefined);tick(1);
assert.match(visible().textContent,/슬롯 수/);assert.equal(visible().getAttribute('role'),'tooltip');
assert.equal(visible().style.left,'688px');assert.equal(visible().style.top,'618px');
listeners.pointerdown();assert.equal(visible(),undefined);assert.equal(canvas.getAttribute('title'),'Native title');
// Unknown/foreign/hidden widgets must keep native behavior and have no timer.
for(const change of [()=>{node.comfyClass='ForeignNode';},()=>{node.widgets[0].hidden=true;},()=>{enabled=false;}]) {
  change();move(canvas);tick(2000);assert.equal(visible(),undefined);
  node.comfyClass='RSMultiCharacterPrompt';delete node.widgets[0].hidden;enabled=true;
}
// A DOM overlay (including multiline textareas) belongs to its own widget.
const input=element('TEXTAREA'), prompt={name:'prompt',inputEl:input};node.widgets.push(prompt);
move(input);tick(2000);assert.match(visible().textContent,/공통 장면/);listeners.wheel();assert.equal(visible(),undefined);
// Vue rows use the field's internal name or visible label without canvas state.
const row={querySelector(sel){return sel==='[aria-label]'?{getAttribute(){return 'character_count';}}:null;}};
const vue=element();vue.closest=sel=>sel==='[data-node-id]'?{dataset:{nodeId:'1'}}:sel.includes('node-widget')?row:null;
move(vue);tick(2000);assert.match(visible().textContent,/슬롯 수/);listeners.blur();
locale='ja';move(canvas);tick(2000);assert.match(visible().textContent,/スロット/);extension.beforeConfigureGraph();assert.equal(visible(),undefined);
// A deleted node must not produce an orphan tooltip when the timer expires.
move(canvas);graph._nodes=[];tick(2000);assert.equal(visible(),undefined);
assert.equal(timers.size,0);
console.log('Widget help: concise locales, 2s timing, cancellation, DOM/canvas/Vue adapters, scope and title restoration passed');
