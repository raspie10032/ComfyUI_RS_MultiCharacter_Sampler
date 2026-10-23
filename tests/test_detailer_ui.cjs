const fs = require('fs'), vm = require('vm'), assert = require('node:assert/strict');
const source = require("./ui_source.cjs")('web/detailer.js').replace(/^import [^\r\n]*\r?\n/gm, '');
let extension;
vm.runInNewContext(source, {
  app: { registerExtension(e) { extension = e; }, ui: { settings: { getSettingValue() { return 'en'; } } } },
  ComfyWidgets: { STRING(node, name) { const widget = {name, type:'text', options:{}, inputEl:{}}; node.widgets.push(widget); return {widget}; } }
});
function nodeClass(values) { return class {
  constructor() { this.widgets = Object.entries(values).map(([name,value]) => ({name,value,type:'combo', computeSize:()=>[300,30],inputEl:{hidden:false}})); this.size=[400,500]; this.inputs=[]; }
  computeSize() { return [400,100]; } setSize(size) { this.size=size; } setDirtyCanvas() {}
}; }
(async () => {
  const Detail = nodeClass({denoise:.35,seed:1,control_after_generate:'fixed',autosave:true,show_advanced:false,steps:20,save_format:'PNG',webp_quality:90});
  await extension.beforeRegisterNodeDef(Detail,{name:'RSMultiCharacterDetailer'});
  const detail = new Detail(); detail.onNodeCreated(); const widget = name=>detail.widgets.find(w=>w.name===name);
  assert.equal(widget('denoise').type,'combo'); assert.equal(widget('steps').hidden,true);
  widget('show_advanced').value=true; widget('show_advanced').callback(); assert.equal(widget('steps').type,'combo'); assert.equal(widget('webp_quality').hidden,true);
  widget('save_format').value='WebP lossy'; widget('save_format').callback(); assert.equal(widget('webp_quality').type,'combo');
  widget('show_advanced').value=false; detail.onConfigure(); assert.equal(widget('steps').value,20); assert.equal(widget('steps').hidden,true); assert.equal(detail.widgets.length,8);
  const Loader=nodeClass({face_segm_model:'segm/face.pt',show_optional_models:false,face_bbox_model:'bbox/face.pt',sam_model:'sam.pt'});
  await extension.beforeRegisterNodeDef(Loader,{name:'RSMultiCharacterDetectionLoader'});
  const loader=new Loader(); loader.onNodeCreated(); const get=name=>loader.widgets.find(w=>w.name===name);
  assert.match(get('rs_detector_plan').value,/SEGM only/); assert.equal(get('face_bbox_model').hidden,true); assert.equal(get('face_bbox_model').value,'bbox/face.pt');
  get('face_segm_model').value='OFF'; get('face_segm_model').callback(); assert.match(get('rs_detector_plan').value,/BBOX \+ SAM/);
  get('sam_model').value='None'; loader.onConfigure(); assert.equal(get('sam_model').value,'OFF'); assert.match(get('rs_detector_plan').value,/rectangles/);
  loader.inputs.push({name:'face_segm_model',link:2}); loader.onConnectionsChange(); assert.match(get('rs_detector_plan').value,/resolved when/);
  assert.equal(get('rs_detector_plan').serializeValue(),undefined); assert.equal(loader.widgets.length,5);
  console.log('Detailer folds preserve values/order; loader precedence/off/link explanations and nonserialized status passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
