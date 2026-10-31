// SPDX-License-Identifier: GPL-3.0-only
import {widget, setValue} from './app_graph.js';

export function promptFields(workspace) {
    const fields = [
        {key:'prompt', label:'공통 프롬프트', node:workspace.sample(), name:'prompt'},
        {key:'negative', label:'공통 네거티브', node:workspace.sample(), name:'negative_prompt'},
    ];
    for (let i = 1; i <= workspace.count(); i++) {
        if (widget(workspace.node('prompt'), `character${i}_enable`)?.value === false
            || widget(workspace.node('prompt'), `character${i}_kind`)?.value === 'text') continue;
        fields.push({key:`character${i}`, label:`캐릭터 ${i}`, node:workspace.node(`text${i}`), name:'value'});
    }
    return fields.map(field => ({...field, text:String(widget(field.node, field.name)?.value ?? '')}));
}

export function restoreTemplates(workspace) {
    const last = workspace.state.wildcardLast;
    if (!last) return;
    for (const {key, node, name, text} of promptFields(workspace)) {
        // Keep edits made in the node graph after loading a generated PNG.
        if (text === last.texts[key] && typeof last.templates[key] === 'string') setValue(node, name, last.templates[key]);
    }
}

export async function resolvePrompts(workspace, fetchApi) {
    const fields = promptFields(workspace), templates = Object.fromEntries(fields.map(f => [f.key, f.text]));
    const seed = Number(widget(workspace.sample(), 'seed').value);
    if (workspace.state.wildcards === false) return {seed, templates, texts:templates};
    const response = await fetchApi('/rs_mc/app/wildcards/resolve', {
        method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({texts:templates, seed}),
    });
    const result = await response.json();
    if (!response.ok) throw Error(result.error ?? `Wildcard: HTTP ${response.status}`);
    for (const key of Object.keys(templates)) if (typeof result.texts?.[key] !== 'string') throw Error('와일드카드 응답에 프롬프트가 누락됐습니다.');
    return {seed, templates, texts:result.texts};
}

export async function expandedPrompt(workspace, expansion, serialize) {
    const fields = promptFields(workspace);
    try {
        for (const field of fields) setValue(field.node, field.name, expansion.texts[field.key]);
        workspace.state.wildcardLast = structuredClone(expansion);
        workspace.route();
        // Store resolved node widgets as well as the original templates. A PNG
        // can replay its actual prompts in the graph without local wildcard files.
        return structuredClone(await serialize());
    } finally {
        for (const field of fields) setValue(field.node, field.name, field.text);
        workspace.route();
    }
}
