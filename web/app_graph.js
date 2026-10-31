// SPDX-License-Identifier: GPL-3.0-only
// The graph is the document. This module only connects existing public nodes.
export const VERSION = 1;
export function widget(node, name) { return node?.widgets?.find(w => w.name === name); }
export function setValue(node, name, value) {
    const w = widget(node, name); if (!w) return false;
    w.value = value; w.callback?.(value); return true;
}
export function inputIndex(node, name) { return node.inputs?.findIndex(x => x.name === name) ?? -1; }
export function outputIndex(node, name) { return node.outputs?.findIndex(x => x.name === name) ?? -1; }
export function connect(from, output, to, input) {
    const a = typeof output === 'number' ? output : outputIndex(from, output), b = inputIndex(to, input);
    if (a < 0 || b < 0) throw Error(`Missing connection: ${from?.type}.${output} → ${to?.type}.${input}`);
    from.connect(a, to, b);
}
export function disconnect(node, name) {
    const i = inputIndex(node, name); if (i >= 0 && node.inputs[i].link != null) node.disconnectInput(i);
}
export function ancestorPrompt(output, end) {
    const wanted = new Set();
    function visit(id) {
        id = String(id); if (wanted.has(id)) return;
        const node = output[id]; if (!node) throw Error(`Missing dependency ${id}`);
        wanted.add(id);
        for (const value of Object.values(node.inputs)) if (Array.isArray(value)) visit(value[0]);
    }
    visit(end);
    return Object.fromEntries([...wanted].map(id => [id, output[id]]));
}

export function executionNodes(graph, saveId) {
    const seen = new Set(), nodes = [];
    function visit(id) {
        if (seen.has(id)) return;
        seen.add(id); const node = graph.getNodeById(id); if (!node) return;
        for (const input of node.inputs ?? []) {
            const link = graph.links[input.link]; if (link) visit(link.origin_id);
        }
        nodes.push(node);
    }
    visit(saveId); return nodes;
}

export class Workspace {
    constructor(graph, createNode, presets) {
        this.graph = graph; this.createNode = createNode; this.presets = presets;
        graph.extra ??= {};
        const old = graph.extra.rs_workspace;
        if (old && old.version !== VERSION) throw Error('Workspace version is newer than this extension.');
        this.state = old ?? {version: VERSION, ids: {}, modelId: '', perModel: {},
            pose: false, camera: false, masks: false, interaction: false,
            progressive: false, detail: false, refs: {}};
        graph.extra.rs_workspace = this.state;
    }
    node(role, type) {
        const id = this.state.ids[role], node = id == null ? null : this.graph.getNodeById(id);
        if (node) {
            if (type && node.type !== type) throw Error(`Workspace node ${role} was replaced; restore its original type.`);
            return node;
        }
        if (!type) return null;
        const fresh = this.createNode(type); if (!fresh) throw Error(`Install the required node: ${type}`);
        fresh.title = `RS App · ${role}`;
        fresh.properties ??= {}; fresh.properties.rs_workspace_role = role;
        fresh.pos = [100 + (Object.keys(this.state.ids).length % 6) * 380, 100 + Math.floor(Object.keys(this.state.ids).length / 6) * 620];
        this.graph.add(fresh); this.state.ids[role] = fresh.id; return fresh;
    }
    initialize() {
        const first = !this.state.ids.prompt;
        this.node('prompt', 'RSMultiCharacterPrompt'); this.node('loras', 'RSMultiCharacterLoRA');
        this.node('position', 'RSMultiCharacterPosition'); this.node('finalize', 'RSMultiCharacterFinalize');
        this.node('sampler', 'RSMultiCharacterSampler'); this.node('progressive', 'RSMultiCharacterProgressiveSampler');
        this.node('masks', 'RSMultiCharacterMaskDraw'); this.node('pose', 'RSMultiCharacterPose3D');
        // Migrate only nodes owned by this workspace. Ordinary user graphs keep
        // their released MODEL adapters and stable output socket numbers.
        const oldPose = this.node('anima_pose') ?? this.node('pose_adapter');
        if (oldPose) {
            for (const [oldName, name] of [['strength','pose_strength'],['start_percent','pose_start'],['end_percent','pose_end']]) {
                const value = widget(oldPose, oldName)?.value;
                if (value !== undefined) setValue(this.node('pose'), name, value);
            }
            setValue(this.node('pose'), 'pose_control', 'auto');
        }
        for (const role of ['anima_pose', 'pose_patch', 'pose_adapter']) {
            const node = this.node(role);
            if (node?.properties?.rs_workspace_role === role) { this.graph.remove?.(node); delete this.state.ids[role]; }
        }
        this.node('camera', 'RSCameraControl'); this.node('interaction', 'RSMultiCharacterInteraction');
        this.node('global_lora', 'LoraLoader'); this.node('save', 'SaveImage');
        if (first) setValue(this.node('save'), 'filename_prefix', 'RS_Workspace');
        for (const role of ['sampler', 'progressive']) {
            const node = this.node(role); setValue(node, 'autosave', false);
            if (first) { setValue(node, 'prompt', 'anime illustration, 2girls, two adult women, walking together in a flowering garden, detailed background'); setValue(node, 'width', 1024); setValue(node, 'height', 1024); }
        }
        if (first) {
            setValue(this.node('prompt'), 'character_count', 2);
            for (let i = 1; i <= 2; i++) {
                const text = this.node(`text${i}`, 'PrimitiveStringMultiline');
                setValue(text, 'value', i === 1 ? 'adult woman, brown hair, blue dress' : 'adult woman, pink hair, white dress');
            }
        }
        this.characters(); return this;
    }
    count() { return Number(widget(this.node('prompt'), 'character_count').value); }
    characters() {
        const count = this.count();
        for (const role of ['loras', 'position']) setValue(this.node(role), 'character_count', count);
        for (let i = 1; i <= count; i++) connect(this.node(`text${i}`, 'PrimitiveStringMultiline'), 0, this.node('prompt'), `character${i}`);
    }
    sample() { return this.node(this.state.progressive ? 'progressive' : 'sampler'); }
    remember() {
        if (!this.state.modelId) return;
        const saved = Object.fromEntries(['sampler', 'progressive', 'loras', 'global_lora', 'camera', 'pose', 'detail', 'detectors', 'tagger'].map(role => [role,
            Object.fromEntries((this.node(role)?.widgets ?? []).filter(w => w.serialize !== false && !['button', 'rs_mc_display'].includes(w.type) && !(role === 'pose' && w.name === 'scene_json')).map(w => [w.name, structuredClone(w.value)]))]));
        saved.globalEnabled = !!this.state.globalLora;
        this.state.perModel[this.state.modelId] = saved;
    }
    select(model) {
        this.remember(); this.state.modelId = model.id; this.model = model;
        const saved = this.state.perModel[model.id];
        const preset = this.presets.find(p => p.id === model.preset);
        if (!preset) throw Error(`Missing model preset: ${model.preset}`);
        for (const role of ['sampler', 'progressive']) for (const [key, value] of Object.entries(preset.settings)) setValue(this.node(role), key, value);
        if (this.node('detail')) for (const key of ['steps','cfg','sampler_name','scheduler']) if (key in preset.settings) setValue(this.node('detail'), key, preset.settings[key]);
        if (!saved) {
            setValue(this.node('global_lora'), 'strength_model', 1); setValue(this.node('global_lora'), 'strength_clip', 1);
            const loras = this.node('loras');
            for (let i = 1; i <= 10; i++) setValue(loras, `character${i}_lora`, 'None');
            this.state.globalLora = false;
        }
        if (saved) for (const [role, values] of Object.entries(saved)) for (const [key, value] of Object.entries(values)) if (this.node(role)) setValue(this.node(role), key, value);
        if (saved) this.state.globalLora = !!saved.globalEnabled;
        this.route(); this.graph.change?.();
    }
    switchSampler(progressive) {
        const previous = this.sample(); this.state.progressive = progressive;
        const next = this.sample();
        for (const w of previous.widgets ?? []) if (w.serialize !== false && widget(next, w.name)) setValue(next, w.name, w.value);
        this.route();
    }
    issues() {
        if (!this.model) return ['Choose an installed model.'];
        const errors = [...this.model.missing], cap = this.model.capabilities;
        if (this.state.masks) {
            try {
                const drawing = JSON.parse(widget(this.node('masks'), 'drawing').value);
                if (!Object.values(drawing.layers ?? {}).some(layer => layer.strokes?.some(stroke => stroke.tool === 'brush' && stroke.points?.length))) errors.push('마스크 그리기를 켰습니다. 먼저 번호를 선택해 영역을 그리거나 기능을 꺼 주세요.');
            } catch { errors.push('마스크 드로잉 데이터를 확인해 주세요.'); }
        }
        const refs = Object.keys(this.state.refs).some(i => Number(i) <= this.count() && this.state.refs[i]);
        if (refs && !cap.reference) errors.push('This checkpoint has no supported image-reference route. FLUX.1 requires Kontext.');
        if (this.model.profile === 'anima29' && Object.keys(this.state.refs).some(i => this.state.refs[i] && Number(i) <= this.count() && widget(this.node(`ref${i}`), 'anima_method')?.value === 'role_kv')) errors.push('Anima 2.9B supports reference_frame; Role K/V weights are for 2B.');
        const learnedPose = this.state.pose && widget(this.node('pose'), 'pose_control')?.value !== 'masks_only' && Number(widget(this.node('pose'), 'pose_strength')?.value ?? 1) > 0;
        if (learnedPose && cap.pose && refs && !cap.pose_reference) errors.push(`${cap.family}: 3D pose adapter + image reference is not supported together. Turn one off; images and scene are preserved.`);
        if (learnedPose && cap.pose && this.state.progressive && !cap.pose_progressive) errors.push(`${cap.family}: 3D pose adapter + progressive resolution is not supported together.`);
        return errors;
    }
    route() {
        if (!this.model) return;
        const model = this.model, cap = model.capabilities;
        this.characters();
        const scene = JSON.parse(widget(this.node('pose'), 'scene_json').value);
        scene.width = Number(widget(this.sample(), 'width').value); scene.height = Number(widget(this.sample(), 'height').value);
        setValue(this.node('pose'), 'scene_json', JSON.stringify(scene));
        setValue(this.node('camera'), 'canvas_aspect', scene.width / scene.height);
        let rawModel, clip, vae;
        if (model.category === 'checkpoints') {
            const loader = this.node('checkpoint', 'CheckpointLoaderSimple'); setValue(loader, 'ckpt_name', model.name);
            rawModel = [loader, 0]; clip = [loader, 1]; vae = [loader, 2];
        } else {
            const loader = this.node('unet', 'UNETLoader'), encoder = this.node('encoder', 'CLIPLoader'), decoder = this.node('vae', 'VAELoader');
            setValue(loader, 'unet_name', model.name); setValue(encoder, 'clip_name', model.encoder);
            setValue(encoder, 'type', model.clip_type); setValue(decoder, 'vae_name', model.vae);
            rawModel = [loader, 0]; clip = [encoder, 0]; vae = [decoder, 0];
        }
        let m = rawModel, c = clip;
        const global = this.node('global_lora');
        if (widget(global, 'lora_name')?.value && widget(global, 'lora_name').value !== 'None' && this.state.globalLora) {
            connect(...m, global, 'model'); connect(...c, global, 'clip'); m = [global, 0]; c = [global, 1];
        }
        const detailModel = m;
        // All pose configuration travels in the editor's building pipe. The
        // sampler owns matching weights, VAE use and native model patching.
        let pipe = null;
        const chain = node => { disconnect(node, 'building_pipe'); if (pipe) connect(pipe, 0, node, 'building_pipe'); pipe = node; };
        if (this.state.pose) chain(this.node('pose'));
        if (this.state.masks) chain(this.node('masks'));
        for (const role of ['prompt', 'loras', 'position']) chain(this.node(role));
        if (this.state.interaction) chain(this.node('interaction'));
        if (this.state.camera) {
            const common = this.node('common_prompt', 'PrimitiveStringMultiline');
            setValue(common, 'value', widget(this.sample(), 'prompt').value);
            connect(common, 0, this.node('camera'), 'base_prompt');
            chain(this.node('camera'));
        }
        for (let i = 1; i <= this.count(); i++) if (this.state.refs[i]) {
            const ref = this.node(`ref${i}`, 'RSMultiCharacterReference'), image = this.node(`image${i}`, 'LoadImage');
            setValue(ref, 'character_id', i); connect(image, 0, ref, 'image'); chain(ref);
        }
        connect(pipe, 0, this.node('finalize'), 'building_pipe');
        const sampler = this.sample();
        connect(...m, sampler, 'model'); connect(...c, sampler, 'clip'); connect(...vae, sampler, 'vae');
        connect(this.node('finalize'), 0, sampler, 'character_pipe');
        const references = Object.keys(this.state.refs).some(i => Number(i) <= this.count() && this.state.refs[i]);
        setValue(sampler, 'layout_method', references ? 'regional' : cap.layout);
        let image = [sampler, 0];
        if (this.state.detail) {
            const firstDetail = !this.node('detail');
            const detail = this.node('detail', 'RSMultiCharacterDetailer'), detectors = this.node('detectors', 'RSMultiCharacterDetectionLoader');
            if (firstDetail) {
                const preset = this.presets.find(p => p.id === model.preset);
                for (const key of ['steps','cfg','sampler_name','scheduler']) if (key in preset.settings) setValue(detail, key, preset.settings[key]);
            }
            connect(...image, detail, 'image'); connect(...detailModel, detail, 'model'); connect(...c, detail, 'clip'); connect(...vae, detail, 'vae');
            connect(sampler, 'character_pipe', detail, 'character_pipe'); connect(detectors, 0, detail, 'detectors');
            // Multiple characters require matching even though this socket is
            // optional in the generic node schema.
            const characters = Array.from({length:this.count()}, (_, i) => i + 1)
                .filter(i => widget(this.node('prompt'), `character${i}_kind`)?.value !== 'text'
                    && widget(this.node('prompt'), `character${i}_enable`)?.value !== false);
            if (characters.length > 1 || this.state.tagger) connect(this.node('tagger', 'RSMultiCharacterTaggerLoader'), 0, detail, 'tagger'); else disconnect(detail, 'tagger');
            setValue(detail, 'autosave', false); image = [detail, 0];
        }
        connect(...image, this.node('save'), 'images');
        this.graph.change?.();
    }
}
