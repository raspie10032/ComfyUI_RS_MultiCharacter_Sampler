// Run against an isolated ComfyUI with this candidate enabled.
// RS_PLAYWRIGHT_MODULE=/absolute/path/to/playwright/index.mjs \
// RS_CHROMIUM=/absolute/path/to/chrome node tools/pose3d/test-editor.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {project} from '../../web/pose3d/model.mjs';
import {gunzipSync} from 'node:zlib';
import {initRig,rigMannequin} from '../../web/pose3d/mhr.mjs';
initRig(JSON.parse(gunzipSync(fs.readFileSync(new URL('../../web/pose3d/mhr-body.json.gz',import.meta.url)))));
const mannequin=p=>rigMannequin(p);
const {chromium}=await import(process.env.RS_PLAYWRIGHT_MODULE||'playwright');
const out=path.resolve(process.env.RS_POSE3D_OUTPUT||'validation-private/pose3d');fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true,...(process.env.RS_CHROMIUM?{executablePath:process.env.RS_CHROMIUM}:{}),args:['--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],requests=[];
page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.frame()!==page.mainFrame()&&/^https?:/.test(r.url())&&!/^http:\/\/(127\.0\.0\.1|localhost):/.test(r.url()))requests.push(r.url());});
const scene=()=>page.evaluate(()=>JSON.parse(rsTestNode.widgets.find(w=>w.name==='scene_json').value));
const frame=page.frameLocator('iframe[title="RS 3D Pose Masks"]');
async function open(){console.log('opening editor');await page.evaluate(()=>rsTestNode.widgets.find(w=>w.type==='button').callback());await frame.locator('#apply').waitFor();await frame.locator('#person option').last().waitFor({state:'attached'});}
async function slide(id,value){await frame.locator('#'+id).fill(String(value));await frame.locator('#'+id).dispatchEvent('input');await frame.locator('#'+id).dispatchEvent('change');}
async function apply(){await frame.locator('#apply').click();await frame.locator('#apply:not(:disabled)').waitFor();await page.waitForTimeout(50);await frame.locator('#status').filter({hasText:/applied|적용|套用/}).waitFor();}
try{
 await page.goto(process.env.RS_COMFY_URL||'http://127.0.0.1:8189/');
 await page.waitForFunction(()=>!!window.comfyAPI?.app?.app?.graph&&!!globalThis.LiteGraph?.registered_node_types.RSMultiCharacterPose3D,null,{timeout:60000});
 // Workflow loading follows node registration during startup.
 await page.waitForTimeout(3000);
 await page.evaluate(()=>{const app=window.comfyAPI.app.app;app.graph.clear();const n=LiteGraph.createNode('RSMultiCharacterPose3D');n.pos=[80,100];app.graph.add(n);window.rsTestNode=n;});
 await open();await frame.locator('#mask-preview').waitFor();await page.waitForTimeout(700);
 await page.screenshot({path:path.join(out,'editor-default.png')});
 const initial=await scene();assert.equal(initial.version,2);
 // Capture scenes produced through real editor controls for generation validation.
 for(const pose of ['seated','wave']){
  await frame.locator('#person').selectOption('1');
  await frame.locator('#preset').selectOption(pose);await frame.locator('#pose').click();await apply();
  fs.writeFileSync(path.join(out,pose+'-scene.json'),JSON.stringify(await scene(),null,2));
  await page.screenshot({path:path.join(out,'editor-'+pose+'-native.png')});
 }
 await frame.locator('#preset').selectOption('standing');await frame.locator('#pose').click();await apply();
 await frame.locator('#joint').selectOption('left_index1');await slide('angle0',50);await apply();
 assert.equal((await scene()).people[0].joints.left_index1[0],50);
 await frame.locator('#undo').click();await apply();assert.deepEqual(await scene(),initial);

 await frame.locator('#joint').selectOption('left_shoulder');await slide('angle2',-70);await slide('scale',.84);
 await frame.locator('#undo').click();assert.equal(Number(await frame.locator('#scale').inputValue()),1);
 await frame.locator('#redo').click();assert.equal(Number(await frame.locator('#scale').inputValue()),.84);
 await apply();let s=await scene();assert.equal(s.people[0].scale,.84);assert.equal(s.people[0].joints.left_shoulder[2],-70);
 await page.screenshot({path:path.join(out,'editor-wave.png')});
 // Actual translation gizmo drag, not a synthetic widget assignment.
 await frame.locator('#move').click();const rect=await frame.locator('#viewport canvas').boundingBox();
 const pelvis=mannequin(s.people[0]).points.pelvis,q=project([pelvis],s.camera,s.width,s.height)[0];
 const x=rect.x+q[0]/s.width*rect.width,y=rect.y+q[1]/s.height*rect.height;
 await page.mouse.move(x+40,y);await page.mouse.down();await page.mouse.move(x+90,y,{steps:12});await page.mouse.up();
 await apply();let moved=await scene();assert.ok(Math.abs(moved.people[0].position[0]-s.people[0].position[0])>.01,'translation gizmo must change the scene');
 await frame.locator('#undo').click();await apply();let undone=await scene();assert.ok(Math.abs(undone.people[0].position[0]-s.people[0].position[0])<1e-6);
 // Actual local rotation-ring drag, then undo to the saved joint angles.
 await frame.locator('#rotate').click();const joint=mannequin(undone.people[0]).points.left_shoulder,jp=project([joint],undone.camera,undone.width,undone.height)[0];
 const rr=await frame.locator('#viewport canvas').boundingBox();
 const distance=Math.hypot(...joint.map((v,i)=>v-undone.camera.position[i]));
 // Three.js screen-facing E ring: .75 * (distance * 1.9*tan(fov/2) * size/4).
 const radius=rr.height*.1425*distance/jp[2];
 const jx=rr.x+jp[0]/undone.width*rr.width,jy=rr.y+jp[1]/undone.height*rr.height;
 await page.mouse.move(jx+radius,jy);await page.mouse.down();await page.mouse.move(jx+radius*.86,jy-radius*.5,{steps:12});await page.mouse.up();
 await apply();const rotated=await scene();assert.notDeepEqual(rotated.people[0].joints.left_shoulder,undone.people[0].joints.left_shoulder,'rotation-ring drag must change joint angles');
 await frame.locator('#undo').click();await apply();undone=await scene();assert.deepEqual(undone.people[0].joints.left_shoulder,s.people[0].joints.left_shoulder);
 // Orbit the output camera in empty space, and roundtrip its orientation.
 await page.mouse.move(rect.x+rect.width-35,rect.y+65);await page.mouse.down();await page.mouse.move(rect.x+rect.width-105,rect.y+95,{steps:8});await page.mouse.up();
 await apply();s=await scene();assert.notDeepEqual(s.camera.position,undone.camera.position);
 // Explicit numbering survives reordering; add/copy/remove and mode switches.
 await frame.locator('#number').fill('3');await frame.locator('#number').dispatchEvent('change');
 await frame.locator('#copy').click();assert.equal(await frame.locator('#person option').count(),3);
 await frame.locator('#remove').click();assert.equal(await frame.locator('#person option').count(),2);
 await frame.locator('#mask-mode').selectOption('visible');await apply();s=await scene();assert.deepEqual(s.people.map(p=>p.id),[2,3]);assert.equal(s.mask_mode,'visible');
 // Save/load a real scene file, including validation of an edited scene.
 const downloadPromise=page.waitForEvent('download');await frame.locator('#save').click();const download=await downloadPromise;const scenePath=path.join(out,'scene.json');await download.saveAs(scenePath);
 assert.deepEqual(JSON.parse(fs.readFileSync(scenePath)),s);
 await frame.locator('#front').click();await frame.locator('#file').setInputFiles(scenePath);await frame.locator('#status').filter({hasText:'Edit the scene'}).waitFor();await apply();
 assert.deepEqual(await scene(),s);
 await page.locator('.rs-pose3d-modal > div > button').click();await open();await apply();assert.deepEqual(await scene(),s);
 // Closing without Apply does not change the stored scene.
 await slide('bulk',1.2);await page.locator('.rs-pose3d-modal > div > button').click();assert.deepEqual(await scene(),s);
 // Workflow reload keeps only the saved scene (no DOM widgets in JSON).
 console.log('reloading workflow');const graph=await page.evaluate(()=>window.comfyAPI.app.app.graph.serialize());fs.writeFileSync(path.join(out,'workflow.json'),JSON.stringify(graph,null,2));
 await page.evaluate(async graph=>{const app=window.comfyAPI.app.app;await app.loadGraphData(graph);window.rsTestNode=app.graph._nodes.find(n=>n.comfyClass==='RSMultiCharacterPose3D');},graph);
 assert.deepEqual(await scene(),s);await open();await apply();assert.deepEqual(await scene(),s);
 await page.screenshot({path:path.join(out,'editor-roundtrip.png')});
 assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
 fs.writeFileSync(path.join(out,'summary.json'),JSON.stringify({errors,externalRequests:requests,scene:s,checks:['WebGL renderer','joint and height controls','undo/redo','translation gizmo mouse drag','rotation gizmo mouse drag','camera orbit','explicit character numbering','copy/remove','full/visible mask mode','scene download/import','cancel','workflow reload']},null,2));
 console.log('3D editor: rendering, gizmo drag, camera, numbering, mask mode, scene/workflow persistence and offline isolation passed');
}catch(e){await page.screenshot({path:path.join(out,'failure.png')});console.error({errors,requests});throw e;}finally{await browser.close();}
