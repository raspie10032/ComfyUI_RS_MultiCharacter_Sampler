// SPDX-License-Identifier: GPL-3.0-only
import {app} from '../../scripts/app.js';
import {api} from '../../scripts/api.js';
import {Workspace, widget, setValue, ancestorPrompt, executionNodes} from './app_graph.js';
import {promptFields, restoreTemplates, resolvePrompts, expandedPrompt} from './app_wildcards.js';

let overlay, workspace, models = [], currentTab = 'characters', mounted = [], activePrompt, busy = false, runningWorkspace;
let wildcardFiles = [], wildcardPreview;
const el = (tag, text, parent, cls) => {
    const node = document.createElement(tag); if (text != null) node.textContent = text;
    if (cls) node.className = cls; parent?.append(node); return node;
};
function button(text, parent, callback) {
    const b = el('button', text, parent); b.type = 'button';
    b.onclick = () => Promise.resolve().then(callback).catch(report); return b;
}
function report(error) { if (overlay) overlay.querySelector('.rs-app-status').textContent = error?.message ?? String(error); }
function change(node, name, value) {
    app.graph.beforeChange?.();
    try { setValue(node, name, value); app.graph.change?.(); }
    finally { app.graph.afterChange?.(); }
}
function restoreDOM() {
    for (const {element, marker, style} of mounted) {
        if (marker.parentNode) marker.replaceWith(element);
        if (style == null) element.removeAttribute('style'); else element.setAttribute('style', style);
    }
    mounted = [];
}
function mountEditor(node, name, parent) {
    const w = widget(node, name), element = w?.element;
    if (!element) { el('p', '편집기를 불러오는 중입니다. 탭을 다시 열어 주세요.', parent); return; }
    const marker = document.createComment('RS workspace editor'); element.before(marker);
    mounted.push({element, marker, style: element.getAttribute('style')});
    const host = el('div', null, parent, 'rs-app-editor'); host.append(element);
    element.style.cssText = 'position:relative!important;transform:none!important;width:100%!important;height:auto!important;min-height:350px;display:block!important;visibility:visible!important;';
}
function choices(w) { const values = w.options?.values; return typeof values === 'function' ? values() : values; }
function field(node, name, parent, label) {
    const w = widget(node, name); if (!w || w.serialize === false || w.type === 'button') return;
    const row = el('label', null, parent, 'rs-app-field'); el('span', label ?? name.replaceAll('_', ' '), row);
    const options = choices(w); let input;
    if (Array.isArray(options)) {
        input = el('select', null, row);
        for (const value of options) { const option = el('option', String(value), input); option.value = String(value); }
        input.value = String(w.value);
    } else if (typeof w.value === 'boolean') {
        input = el('input', null, row); input.type = 'checkbox'; input.checked = w.value;
    } else if (typeof w.value === 'number') {
        input = el('input', null, row); input.type = 'number'; input.value = w.value;
        input.step = 'any'; if (Number.isFinite(w.options?.min)) input.min = w.options.min;
        if (Number.isFinite(w.options?.max)) input.max = Math.min(w.options.max, Number.MAX_SAFE_INTEGER);
    } else if (typeof w.value === 'string') {
        input = el('textarea', null, row); input.value = w.value; input.rows = name === 'scene_json' || name === 'drawing' ? 5 : 3;
    } else { row.remove(); return; }
    input.dataset.widget = name; input.title = w.options?.tooltip ?? name;
    input.onchange = () => {
        try {
            let value = input.type === 'checkbox' ? input.checked : input.type === 'number' ? Number(input.value) : input.value;
            if (input.type === 'number' && (!input.checkValidity() || !Number.isFinite(value))) throw Error(`${name}: 수치 범위를 확인해 주세요.`);
            change(node, name, value); wildcardPreview=null;
            if (currentTab === 'wildcards') overlay?.querySelector('.rs-app-wildcard-preview')?.remove();
            if (name === 'character_count') { workspace.characters(); render(); }
            else if (name.endsWith('_kind') || name === 'anima_method') render();
        } catch (error) { report(error); }
    };
    return input;
}
function fields(node, parent, names) { for (const name of names ?? (node.widgets ?? []).map(w => w.name)) field(node, name, parent); }
function section(title, parent) { const box = el('section', null, parent, 'rs-app-card'); el('h3', title, box); return box; }
function advanced(node, parent, omit = []) {
    const details = el('details', null, parent); el('summary', '세부 설정 · Advanced', details);
    fields(node, details, (node.widgets ?? []).map(w => w.name).filter(n => !omit.includes(n)));
}
function toggle(key, label, parent) {
    const row = el('label', null, parent, 'rs-app-toggle'), box = el('input', null, row);
    box.type = 'checkbox'; box.checked = !!workspace.state[key]; el('span', label, row);
    box.onchange = () => {
        try {
            if (key === 'progressive') workspace.switchSampler(box.checked);
            else { workspace.state[key] = box.checked; workspace.route(); }
            render();
        } catch (error) { report(error); }
    };
}
function modelNotice(parent) {
    const cap = workspace.model?.capabilities;
    if (!cap) return;
    const pose = cap.pose === 'lllite' ? 'Anima LLLite' : cap.pose === 'scene_adapter' ? `${cap.family} 전용 어댑터` : '영역 마스크 유도 (학습된 포즈 어댑터 없음)';
    el('p', `${cap.family} · 3D: ${pose} · 배치: ${cap.layout} · 참조: ${cap.reference ? (cap.reference_method === 'frame' ? 'Anima Reference Frame' : '모델별 참조') : '현재 체크포인트 미지원'}`, parent, 'rs-app-hint');
    if (cap.note) el('p', cap.note, parent);
    for (const error of workspace.issues()) el('p', error, parent, 'rs-app-error');
}
function render() {
    restoreDOM();
    const content = overlay.querySelector('.rs-app-content'); content.replaceChildren();
    const side = el('aside', null, content), main = el('main', null, content);
    const model = section('모델 · Model', side), select = el('select', null, model);
    select.setAttribute('aria-label', 'Model'); el('option', '모델 선택', select).value = '';
    for (const item of models) { const option = el('option', `[${item.capabilities.family}] ${item.name}`, select); option.value = item.id; }
    select.value = workspace.state.modelId;
    select.onchange = () => { try { const m = models.find(m => m.id === select.value); if (m) { workspace.select(m); render(); } } catch (error) { report(error); } };
    modelNotice(model);
    const controls = section('제어 · Controls', side);
    for (const [key, label] of [['pose', '3D 포즈'], ['masks', '마스크 그리기'], ['camera', '카메라'], ['interaction', '상호작용 경계'], ['progressive', '점진 해상도'], ['detail', '얼굴 디테일러'], ['globalLora', '전역 LoRA']]) toggle(key, label, controls);
    el('p', '모델을 바꿔도 프롬프트·마스크·3D 장면은 보존됩니다. 지원하지 않는 동시 조합은 생성 전에 표시됩니다.', side, 'rs-app-hint');
    const tabs = el('nav', null, main, 'rs-app-tabs');
    for (const [id, label] of [['characters','캐릭터'], ['wildcards','와일드카드'], ['layout','배치 / 마스크'], ['pose','3D 포즈'], ['camera','카메라'], ['settings','생성 / 보정'], ['results','결과']]) {
        const b = button(label, tabs, () => { currentTab = id; render(); }); b.classList.toggle('selected', id === currentTab);
    }
    const panel = el('div', null, main, 'rs-app-panel');
    if (currentTab === 'characters') characters(panel);
    if (currentTab === 'wildcards') wildcards(panel);
    if (currentTab === 'layout') {
        const position = section('번호 선택 → 드래그로 배치·크기 조절', panel);
        mountEditor(workspace.node('position'), 'rs_mc_position_editor', position);
        advanced(workspace.node('position'), position);
        if (workspace.state.masks) {
            const draw = section('마스크 그리기 · 같은 캐릭터 번호 사용', panel);
            mountEditor(workspace.node('masks'), 'rs_mc_mask_editor', draw); field(workspace.node('masks'), 'margin', draw);
        }
        el('p', '마스크는 대략적인 조건 영역입니다. 캔버스 밖은 잘립니다. MOSS native에서는 외접 사각형으로 변환됩니다.', panel);
    }
    if (currentTab === 'pose') {
        workspace.route();
        const box = section('3D 장면 · 포즈·카메라·인물 번호', panel), node = workspace.node('pose');
        const open = node.widgets?.find(w => w.type === 'button');
        if (open) button('3D 편집기 열기', box, () => {
            const canvas = document.createElement('canvas');
            if (!canvas.getContext('webgl2')) throw Error('현재 브라우저는 WebGL2를 지원하지 않습니다. GPU 가속이 켜진 Chrome 또는 Firefox에서 3D 편집기를 열어 주세요. 저장된 장면으로 생성은 가능합니다.');
            return open.callback?.();
        });
        mountEditor(node, 'pose3d_import', box); mountEditor(node, 'pose3d_preview', box); mountEditor(node, 'pose3d_status', box);
        if (workspace.state.pose) {
            const cap = workspace.model?.capabilities;
            for (const name of ['pose_control', 'pose_strength', 'pose_start', 'pose_end']) field(node, name, box);
        }
        advanced(node, box);
    }
    if (currentTab === 'camera') {
        const box = section('카메라 시점·거리·기울기', panel), node = workspace.node('camera');
        for (const w of node.widgets ?? []) if (w.element) mountEditor(node, w.name, box);
        fields(node, box);
        if (workspace.state.interaction) fields(workspace.node('interaction'), section('상호작용 경계 해제', panel));
    }
    if (currentTab === 'settings') {
        const sample = workspace.sample(), box = section('공통 프롬프트와 생성 설정', panel);
        const primary = ['prompt','negative_prompt','width','height','seed','steps','cfg','sampler_name','scheduler', 'start_scale'];
        fields(sample, box, primary); advanced(sample, box, primary);
        if (workspace.state.globalLora) fields(workspace.node('global_lora'), section('전역 LoRA', panel));
        if (workspace.state.detail) {
            const d = section('얼굴 보정 · 생성 모델과 캐릭터 파이프 자동 연결', panel);
            fields(workspace.node('detail'), d); fields(workspace.node('detectors'), d);
            if (workspace.count() <= 1) toggle('tagger', 'WD 태거로 캐릭터 매칭', d);
            if (workspace.node('tagger') && workspace.node('detail').inputs.some(input => input.name === 'tagger' && input.link != null)) {
                el('p', '여러 캐릭터는 원래 프롬프트를 구분하기 위해 태거가 자동 연결됩니다.', d);
                fields(workspace.node('tagger'), d);
            }
        }
        fields(workspace.node('save'), section('저장', panel));
    }
    if (currentTab === 'results') renderResults(panel);
    const run = overlay.querySelector('[data-action="generate"]'); run.disabled = busy || workspace.issues().length > 0;
    for (const control of content.querySelectorAll('input,select,textarea,button')) control.disabled = busy;
}
function characters(parent) {
    el('p', '__fabe__ · __ff__ · {선택지 A|선택지 B}를 프롬프트에 쓸 수 있습니다. 와일드카드 탭에서 파일 선택·미리보기를 할 수 있어요. 글자 영역은 입력 그대로 사용합니다.', parent, 'rs-app-hint');
    field(workspace.node('prompt'), 'character_count', parent, '캐릭터 / 글자 영역 수');
    const loras = workspace.node('loras'); field(loras, 'lora_application_mode', parent, '캐릭터 LoRA 적용 방식');
    for (let i = 1; i <= workspace.count(); i++) {
        const box = section(`영역 ${i}`, parent), prompt = workspace.node('prompt');
        field(prompt, `character${i}_enable`, box, '사용'); field(prompt, `character${i}_kind`, box, '캐릭터 / 글자');
        field(workspace.node(`text${i}`), 'value', box, widget(prompt, `character${i}_kind`).value === 'text' ? '넣을 글자' : '캐릭터 프롬프트');
        for (const name of [`character${i}_lora`,`character${i}_lora_strength`,`character${i}_lora_clip_strength`]) field(loras, name, box);
        const ref = el('label', null, box, 'rs-app-toggle'), check = el('input', null, ref); check.type = 'checkbox'; check.checked = !!workspace.state.refs[i]; el('span','참조 이미지 사용',ref);
        check.onchange = () => { try { workspace.state.refs[i] = check.checked; workspace.route(); render(); } catch (error) { report(error); } };
        if (check.checked) {
            const image = workspace.node(`image${i}`); field(image, 'image', box, '참조 이미지');
            const upload = el('input', null, box); upload.type = 'file'; upload.accept = 'image/png,image/jpeg,image/webp';
            upload.onchange = async () => {
                try {
                    const file = upload.files?.[0]; if (!file) return;
                    const body = new FormData(); body.append('image', file); body.append('type', 'input'); body.append('subfolder', 'RS_Workspace');
                    const response = await api.fetchApi('/upload/image', {method:'POST', body});
                    if (!response.ok) throw Error(`Image upload: HTTP ${response.status}`);
                    const result = await response.json(), name = [result.subfolder, result.name].filter(Boolean).join('/');
                    const w = widget(image,'image'); if (Array.isArray(w.options?.values) && !w.options.values.includes(name)) w.options.values.push(name);
                    change(image,'image',name); render();
                } catch (error) { report(error); }
            };
            fields(workspace.node(`ref${i}`), box, ['resolution','strength','anima_method']);
        }
    }
}
async function loadWildcards() {
    const response = await api.fetchApi('/rs_mc/app/wildcards');
    if (!response.ok) throw Error(`Wildcard inventory: HTTP ${response.status}. ComfyUI를 재시작해 주세요.`);
    wildcardFiles = (await response.json()).files;
}
function wildcards(parent) {
    const box = section('로컬 와일드카드 · 파일 선택 → 프롬프트에 넣기', parent);
    const enabled = el('label', null, box, 'rs-app-toggle'), check = el('input', null, enabled);
    check.type='checkbox'; check.checked=workspace.state.wildcards !== false; el('span','와일드카드 펼치기',enabled);
    check.onchange=()=>{workspace.state.wildcards=check.checked;wildcardPreview=null;workspace.graph.change?.();render();};
    el('p','공통·네거티브·캐릭터 프롬프트에서 __파일명__ 또는 {A|B}를 사용하세요. 생성 시드가 같으면 선택도 같습니다. 랜덤 시드는 매 생성마다 다시 선택합니다. 글자 영역은 변환하지 않습니다.',box,'rs-app-hint');
    const search=el('input',null,box);search.type='search';search.placeholder='파일 검색 · fabe / ff / background';search.setAttribute('aria-label','와일드카드 파일 검색');
    const list=el('select',null,box);list.size=8;list.setAttribute('aria-label','와일드카드 파일');
    function fill() {
        list.replaceChildren();
        for(const name of wildcardFiles.filter(name=>name.toLowerCase().includes(search.value.toLowerCase()))) {
            const option=el('option',name,list);option.value=name;
        }
    }
    search.oninput=fill;fill();
    button('파일 목록 새로고침',box,async()=>{await loadWildcards();fill();report(`와일드카드 ${wildcardFiles.length}개`);});
    const target=el('select',null,box);target.setAttribute('aria-label','삽입할 프롬프트');
    const fields=promptFields(workspace);
    for(const field of fields) el('option',field.label,target).value=field.key;
    button('선택한 파일 넣기',box,()=>{
        if(!list.value) throw Error('먼저 와일드카드 파일을 선택해 주세요.');
        const field=fields.find(field=>field.key===target.value), old=String(widget(field.node,field.name).value);
        change(field.node,field.name,old+(old.trim()?', ':'')+`__${list.value}__`);wildcardPreview=null;render();
    });
    el('p',`파일 ${wildcardFiles.length}개 · ComfyUI/user/wildcards, ComfyUI/wildcards와 설치된 확장의 wildcards·custom_wildcards 폴더에서 TXT를 읽습니다. 빈 줄·# 주석은 제외합니다. 추가한 뒤 목록을 새로고침하세요.`,box,'rs-app-hint');
    for(const item of fields) field(item.node,item.name,box,item.label);
    button('현재 시드로 미리보기',box,async()=>{
        const owner=workspace, preview=await resolvePrompts(owner,api.fetchApi.bind(api));
        if(owner!==workspace)return;
        wildcardPreview=preview;render();
    });
    const preview=wildcardPreview??workspace.state.wildcardLast;
    if(preview) {
        const result=section(`${wildcardPreview ? '미리보기' : '최근 생성 요청'} · 펼친 프롬프트 · 시드 ${preview.seed}`,parent);
        result.classList.add('rs-app-wildcard-preview');
        el('p','미리보기는 해당 시드의 예상 선택입니다. 랜덤 시드 생성에서는 달라질 수 있습니다. 완료 결과의 PNG에는 실제 사용한 프롬프트와 원래 템플릿을 함께 저장합니다.',result,'rs-app-hint');
        for(const [key,text] of Object.entries(preview.texts)) {el('strong',fields.find(f=>f.key===key)?.label??key,result);el('pre',text,result);}
    }
}
function renderResults(parent) {
    const outputs = workspace.state.results ?? [];
    if (!outputs.length) el('p', '생성 완료 후 결과가 여기에 표시됩니다.', parent);
    for (const image of outputs) {
        const link = el('a', null, parent); link.href = api.apiURL('/view?'+new URLSearchParams(image)); link.target = '_blank';
        const img = el('img', null, link); img.src = link.href; img.alt = image.filename; img.style.maxWidth = 'min(100%, 700px)';
    }
}
async function generate() {
    if (busy) return;
    workspace.route(); const issues = workspace.issues(); if (issues.length) throw Error(issues.join('\n'));
    busy = true; render(); report('큐에 등록하는 중…');
    try {
        const nodes = executionNodes(workspace.graph, workspace.node('save').id);
        for (const node of nodes) for (const control of node.widgets ?? []) control.beforeQueued?.({isPartialExecution:true});
        workspace.route();
        const expansion = await resolvePrompts(workspace, api.fetchApi.bind(api));
        const full = await expandedPrompt(workspace, expansion, () => app.graphToPrompt());
        const output = ancestorPrompt(full.output, workspace.node('save').id);
        const queued = await api.queuePrompt(0, {output, workflow:full.workflow});
        if (!queued.prompt_id) throw Error(queued.error?.message ?? 'Prompt rejected');
        activePrompt = queued.prompt_id; runningWorkspace = workspace; workspace.state.lastPrompt = activePrompt; report('생성 대기 · '+activePrompt);
        for (const node of nodes) for (const control of node.widgets ?? []) control.afterQueued?.({isPartialExecution:true});
        workspace.graph.change?.();
    } catch (error) { busy = false; render(); throw error; }
}
async function openWorkspace() {
    if (overlay) return;
    if (busy) throw Error('현재 앱 생성이 끝난 뒤 다시 열어 주세요.');
    const response = await api.fetchApi('/rs_mc/app/models');
    if (!response.ok) throw Error(`Model inventory: HTTP ${response.status}. Restart ComfyUI after installing this extension.`);
    models = (await response.json()).models;
    const presets = await (await fetch(new URL('./model_presets.json',import.meta.url))).json();
    // A workspace owns a dedicated graph tab. Let the frontend retain the
    // current workflow and its unsaved edits before initializing our nodes.
    if (!app.graph.extra?.rs_workspace && app.graph._nodes?.length) {
        if (!app.extensionManager?.command?.execute) throw Error('빈 워크플로 탭에서 RS Workspace를 열어 주세요.');
        await app.extensionManager.command.execute('Comfy.NewBlankWorkflow');
    }
    workspace = new Workspace(app.graph, type => LiteGraph.createNode(type), presets).initialize();
    const saved = models.find(m => m.id === workspace.state.modelId);
    if (saved) { workspace.model = saved; restoreTemplates(workspace); workspace.route(); }
    wildcardPreview=null;
    try { await loadWildcards(); } catch(error) { wildcardFiles=[]; console.warn('RS Workspace wildcards',error); }
    overlay = el('div', null, document.body, 'rs-app-workspace'); overlay.setAttribute('role','dialog'); overlay.setAttribute('aria-label','RS Model Workspace');
    const header = el('header', null, overlay); el('strong','RS Workspace · 모델 자동 연결 시험판',header);
    button('생성',header,generate).dataset.action = 'generate';
    button('워크플로 저장',header,async () => {
        workspace.remember(); const data = (await app.graphToPrompt()).workflow;
        const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
        const link=el('a');link.href=url;link.download='RS-Workspace.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    });
    button('노드 그래프',header,() => {restoreDOM();overlay.remove();overlay=null;});
    el('div',null,overlay,'rs-app-content'); el('p','모델을 선택하고 장면을 편집해 주세요.',overlay,'rs-app-status'); render();
}
app.registerExtension({name:'RS.MultiCharacter.Workspace',
    commands:[{id:'rs-model-workspace',label:'RS Model Workspace (Experimental)',function:() => openWorkspace().catch(error => app.extensionManager.toast.add({severity:'error',summary:'RS Workspace',detail:error.message,life:10000}))}],
    menuCommands:[{path:['Edit'],commands:['rs-model-workspace']}],
    setup() {
        const link = el('link'); link.rel='stylesheet';link.href=new URL('./app_workspace.css',import.meta.url).href;document.head.append(link);
        // Persistent entry point even when the frontend's menu placement changes.
        const launch=button('RS Workspace',document.body,openWorkspace); launch.className='rs-app-launch';
        api.addEventListener('progress', event => {if(busy && overlay) report(`생성 중 ${event.detail.value} / ${event.detail.max}`);});
        api.addEventListener('executed', event => {
            if (event.detail.prompt_id !== activePrompt || !runningWorkspace) return;
            if (String(event.detail.node) === String(runningWorkspace.node('save').id)) {
                runningWorkspace.state.results=[...(event.detail.output?.images ?? []),...(runningWorkspace.state.results??[])].slice(0,30);
                if (overlay && currentTab==='results') render();
            }
        });
        for (const type of ['execution_success','execution_error','execution_interrupted']) api.addEventListener(type,event=>{
            if(event.detail.prompt_id!==activePrompt)return;
            busy=false;activePrompt=null;runningWorkspace=null;if(overlay){render();report(type==='execution_success'?'생성·저장 완료':event.detail.exception_message??'생성이 중단되었습니다.');}
        });
    },
    beforeConfigureGraph() {
        if (overlay) { restoreDOM(); overlay.remove(); overlay = null; }
    },
});
