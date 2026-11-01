// SPDX-License-Identifier: GPL-3.0-only
// Small, offline fallback. Third-party autocomplete keeps ownership of native
// widgets when enabled. An optional local autocomplete.txt supplies custom tags.
import {app} from '../../scripts/app.js';
import {api} from '../../scripts/api.js';

export const BASIC_TAGS = (`
1girl|2girls|3girls|4girls|5girls|6girls|1boy|2boys|solo|duo|group|adult woman|adult man|
anime illustration|masterpiece|best quality|high quality|highres|detailed background|simple background|white background|transparent background|
full body|upper body|portrait|close-up|cowboy shot|wide shot|standing|sitting|lying|kneeling|crouching|walking|running|jumping|dancing|leaning forward|leaning back|
from above|from below|from side|from behind|front view|back view|side view|three-quarter view|looking at viewer|looking away|looking back|eye contact|
smile|open mouth|closed mouth|blush|laughing|crying|surprised|angry|sleepy|closed eyes|wink|head tilt|
short hair|long hair|very long hair|medium hair|straight hair|wavy hair|curly hair|braid|twin braids|ponytail|twintails|bob cut|bangs|hair between eyes|hair ornament|hair ribbon|hair clip|
black hair|brown hair|blonde hair|white hair|silver hair|grey hair|red hair|orange hair|pink hair|purple hair|blue hair|green hair|multicolored hair|
blue eyes|green eyes|red eyes|brown eyes|purple eyes|yellow eyes|grey eyes|heterochromia|glasses|freckles|
dress|white dress|black dress|blue dress|pink dress|chiffon dress|long dress|short dress|shirt|white shirt|blouse|skirt|pleated skirt|long skirt|pants|shorts|jeans|jacket|coat|cardigan|sweater|turtleneck|hoodie|uniform|suit|robe|cape|apron|hat|beret|witch hat|ribbon|bow|necklace|earrings|gloves|boots|shoes|sneakers|sandals|stockings|socks|tights|
long sleeves|short sleeves|sleeveless|frills|lace|embroidery|floral print|striped clothes|matching outfits|
holding hands|hugging|arm around shoulder|back-to-back|cheek-to-cheek|high five|handshake|reaching out|pointing|waving|arms up|arms crossed|hands on hips|hand on own chest|hand on own head|hand on another's shoulder|
reading|book|writing|drawing|painting|cooking|eating|drinking|tea|coffee|cup|cake|flower|bouquet|umbrella|bag|camera|guitar|piano|sword|staff|magic|
indoors|outdoors|bedroom|living room|kitchen|library|classroom|cafe|restaurant|balcony|terrace|garden|park|forest|flower field|beach|ocean|mountain|river|lake|waterfall|street|city|town|castle|university campus|
spring|summer|autumn|winter|day|night|morning|sunset|sunrise|blue sky|clouds|starry sky|rain|snow|wind|falling leaves|cherry blossoms|
sunlight|moonlight|soft lighting|warm lighting|rim lighting|backlighting|volumetric lighting|cinematic lighting|depth of field|bokeh|reflection|shadow|
watercolor|oil painting|sketch|lineart|no lineart|flat color|cel shading|painterly|soft shading|vibrant colors|pastel colors|muted colors|
bad quality|worst quality|low quality|lowres|blurry|jpeg artifacts|watermark|signature|text|logo|bad anatomy|bad hands|extra fingers|missing fingers|extra arms|extra legs|extra limbs|duplicate|cropped|out of frame
`).split('|').map(s => s.trim()).filter(Boolean).sort();
const attached = new WeakMap();
let nextMenu = 0;
let enabled = true, wildcardNames = [], wildcardPending, wildcardLoaded = false;
let dictionary = [], dictionaryPending;
const normalize = text => text.toLowerCase().replaceAll('_', ' ').trim();

export function parseDictionary(text) {
    const entries = new Map();
    for (const line of text.replace(/^\uFEFF/, '').split(/\r?\n/)) {
        if (!line.trim()) continue;
        const fields = []; let field = '', quoted = false;
        for (let i = 0; i < line.length; i++) {
            const char = line[i];
            if (char === '"') {
                if (quoted && line[i + 1] === '"') {field += '"'; i++;}
                else quoted = !quoted;
            } else if (char === ',' && !quoted) {fields.push(field.trim()); field = '';}
            else field += char;
        }
        fields.push(field.trim());
        const value = fields[0];
        if (!value || /^(?:tag|name)$/i.test(value) && /^(?:count|category|type)$/i.test(fields[1] ?? '')) continue;
        const priority = Number(fields.length >= 3 ? fields[2] : fields[1]) || 0;
        const aliases = fields.length >= 4 ? (fields[3] === 'null' ? [] : fields[3].split(',')) : fields.length === 2 && Number.isNaN(Number(fields[1])) ? [fields[1]] : [];
        const key = normalize(value);
        if (!entries.has(key)) entries.set(key, {value, key, priority, aliases:aliases.map(normalize).filter(Boolean)});
    }
    return [...entries.values()].sort((a, b) => b.priority - a.priority);
}
async function loadDictionary() {
    if (!dictionaryPending) dictionaryPending = fetch(new URL('./autocomplete.txt', import.meta.url))
        .then(async response => {if (response.ok) dictionary = parseDictionary(await response.text());})
        .catch(() => {});
    await dictionaryPending;
}

// Character/text drawing inputs remain literal. JSON, paths, seeds and names
// must never receive prompt suggestions.
export function isPromptWidget(node, name) {
    if (/^(?:prompt|negative_prompt|positive|negative|global_prompt|common_prompt)$/.test(name))
        return /^RS/.test(node.type ?? node.comfyClass ?? '');
    const slot = node.properties?.rs_workspace_role?.match(/^text(\d+)$/)?.[1];
    if (!['value', 'text'].includes(name)) return false;
    if (slot) {
        const prompt = node.graph?.getNodeById(node.graph?.extra?.rs_workspace?.ids?.prompt);
        return prompt?.widgets?.find(w => w.name === `character${slot}_kind`)?.value !== 'text';
    }
    // Also support ordinary STRING nodes connected to the character builder.
    // A shared source used by a text slot stays literal to avoid editing titles.
    let character = false;
    for (const output of node.outputs ?? []) for (const id of output.links ?? []) {
        const link = node.graph?.links?.[id], target = node.graph?.getNodeById(link?.target_id);
        if (target?.type !== 'RSMultiCharacterPrompt') continue;
        const input = target.inputs?.[link.target_slot]?.name;
        const number = input?.match(/^character(\d+)$/)?.[1];
        if (!number) continue;
        if (target.widgets?.find(w => w.name === `character${number}_kind`)?.value === 'text') return false;
        character = true;
    }
    return character;
}
export function externalProvider(extensions = [], setting = () => undefined) {
    const names = new Set(extensions.flatMap(ext => [ext.name, ext.id]));
    if ((names.has('ComfyUI.AutocompletePlusPlus') || names.has('Autocomplete++')) && setting('ComfyUI.AutocompletePlusPlus.Enabled') !== false) return 'Autocomplete++';
    if (names.has('AutocompletePlus') && setting('AutocompletePlus.Autocompletion.Enable') !== false) return 'Autocomplete-Plus';
    if (names.has('pysssss.AutoCompleter') && setting('pysssss.AutoCompleter') !== false) return 'Custom Scripts';
    return '';
}
export function currentToken(text, caret, end = caret) {
    if (caret !== end) return null;
    const prefix = text.slice(0, caret), wildcard = prefix.match(/__(?!.*__)([^,\n{}|]*)$/);
    if (wildcard) {
        const start = caret - wildcard[0].length;
        // Reject the closing delimiter of an already complete wildcard.
        if ((prefix.match(/__/g)?.length ?? 0) % 2 === 0) return null;
        const tail = text.slice(caret).match(/^[^,\n{}|]*?(?:__|(?=[,\n{}|]|$))/)?.[0] ?? '';
        return {start, end:caret + tail.length, query:wildcard[1], wildcard:true};
    }
    const segment = prefix.slice(Math.max(prefix.lastIndexOf(','), prefix.lastIndexOf('\n'), prefix.lastIndexOf('|'), prefix.lastIndexOf('{')) + 1);
    const leading = segment.match(/^\s*[([{]*\s*/)[0].length;
    const query = segment.slice(leading);
    if (query.length < 2 || /[:<>\[\]{}]/.test(query) || query.includes('__')) return null;
    const tail = text.slice(caret).match(/^[^,\n:)}\]|]*/)?.[0] ?? '';
    return {start:caret - query.length, end:caret + tail.trimEnd().length, query, wildcard:false};
}
export function suggestions(token, words = BASIC_TAGS, wildcards = []) {
    if (!token) return [];
    const query = normalize(token.query);
    const values = token.wildcard ? wildcards.map(name => `__${name}__`) : words;
    const unique = new Set(), prefix = [], partial = [];
    for (const entry of values) {
        const value = typeof entry === 'string' ? entry : entry.value;
        const key = typeof entry === 'string' ? normalize(token.wildcard ? value.slice(2, -2) : value) : entry.key;
        if (key === query || unique.has(key)) continue;
        const keys = [key, ...(entry.aliases ?? [])];
        if (!keys.some(key => key.includes(query))) continue;
        unique.add(key);
        const matches = keys.some(key => key.startsWith(query)) ? prefix : partial;
        if (matches.length < 8) matches.push(value);
        if (prefix.length === 8) break;
    }
    return [...prefix, ...partial].slice(0, 8);
}
export function completion(text, token, value) {
    const tail = text.slice(token.end);
    const separator = !token.wildcard && (!tail || /^\s*$/.test(tail)) ? ', ' : '';
    if (!token.wildcard) value = value.replace(/(?<!\\)([()])/g, '\\$1');
    const insert = value + separator;
    return {text:text.slice(0, token.start) + insert + tail, caret:token.start + insert.length};
}
export function setWildcardNames(names) { wildcardNames = names.filter(name => typeof name === 'string'); wildcardLoaded = true; }
async function loadWildcards() {
    if (wildcardLoaded) return;
    if (!wildcardPending) wildcardPending = api.fetchApi('/rs_mc/app/wildcards').then(async response => {
        if (response.ok) setWildcardNames((await response.json()).files ?? []);
    }).catch(() => {}).finally(() => { wildcardPending = null; });
    await wildcardPending;
}
function provider() {
    return externalProvider(app.extensions ?? [], id => app.ui?.settings?.getSettingValue(id));
}
export function attachAutocomplete(input, {native = false, eligible = () => true} = {}) {
    if (!input || input.tagName !== 'TEXTAREA' || input.readOnly || attached.has(input)) return;
    let menu, items = [], selected = 0, token, composing = false, destroyed = false;
    const doc = input.ownerDocument;
    const previous = {role:input.getAttribute('role'), autocomplete:input.getAttribute('aria-autocomplete'), expanded:input.getAttribute('aria-expanded')};
    function hide() {
        const visible = Boolean(menu); menu?.remove(); menu = null; items = [];
        if (!visible) return;
        input.removeAttribute('aria-activedescendant'); input.removeAttribute('aria-controls');
        if (input.getAttribute('aria-autocomplete') === 'list') input.setAttribute('aria-expanded', 'false');
    }
    function commit(index) {
        // Another input/caret event may have made a previously rendered token stale.
        const fresh = currentToken(input.value, input.selectionStart, input.selectionEnd);
        if (!fresh || !items[index]) return hide();
        const result = completion(input.value, fresh, items[index]); hide();
        input.focus(); input.value = result.text; input.setSelectionRange(result.caret, result.caret);
        input.dispatchEvent(new Event('input', {bubbles:true})); input.dispatchEvent(new Event('change', {bubbles:true})); hide();
    }
    function draw() {
        menu?.remove(); menu = doc.createElement('div'); menu.className = 'rs-prompt-completions';
        menu.id = `rs-prompt-completions-${++nextMenu}`; menu.setAttribute('role', 'listbox');
        items.forEach((value, i) => {
            const option = doc.createElement('div'); option.textContent = value; option.id = `${menu.id}-option-${i}`;
            option.setAttribute('role', 'option'); option.setAttribute('aria-selected', String(i === selected));
            option.addEventListener('pointerdown', event => {event.preventDefault(); commit(i);}); menu.append(option);
        });
        doc.body.append(menu);
        const rect = input.getBoundingClientRect(), width = Math.max(180, Math.min(rect.width, 440, innerWidth - 16));
        menu.style.width = `${width}px`; menu.style.left = `${Math.max(8, Math.min(rect.left, innerWidth - width - 8))}px`;
        const height = Math.min(menu.scrollHeight, 250);
        menu.style.top = `${Math.max(8, rect.bottom + height > innerHeight ? rect.top - height : rect.bottom)}px`;
        input.setAttribute('role', 'combobox'); input.setAttribute('aria-autocomplete', 'list');
        input.setAttribute('aria-expanded', 'true'); input.setAttribute('aria-controls', menu.id);
        input.setAttribute('aria-activedescendant', `${menu.id}-option-${selected}`);
    }
    async function update(event) {
        hide();
        if (destroyed || !eligible() || !enabled || composing || event?.isComposing || doc.activeElement !== input || (native && provider())) return;
        token = currentToken(input.value, input.selectionStart, input.selectionEnd);
        if (token?.wildcard && !wildcardLoaded) { await loadWildcards(); if (destroyed || !eligible() || !enabled || doc.activeElement !== input || composing || (native && provider())) return; token = currentToken(input.value, input.selectionStart, input.selectionEnd); }
        if (token && !token.wildcard) {
            await loadDictionary();
            if (destroyed || !eligible() || !enabled || doc.activeElement !== input || composing || (native && provider())) return;
            token = currentToken(input.value, input.selectionStart, input.selectionEnd);
        }
        // Reuse words already in this graph, without retaining prompt history.
        const words = [...dictionary, ...BASIC_TAGS];
        if (!token?.wildcard) for (const node of app.graph?._nodes ?? []) for (const w of node.widgets ?? [])
            if (isPromptWidget(node, w.name) && typeof w.value === 'string') words.push(...w.value.split(/[,\n]/).map(s => s.trim()).filter(s => s.length >= 2 && s.length <= 100 && !/[{}<>]|__/.test(s)));
        items = suggestions(token, words, wildcardNames); selected = 0; if (items.length) draw();
    }
    function keydown(event) {
        if (!eligible() || !enabled || (native && provider())) return hide();
        if (composing || event.isComposing || event.keyCode === 229) return;
        if (event.ctrlKey && !event.metaKey && !event.altKey && event.code === 'Space') {
            event.preventDefault(); event.stopPropagation(); void update(); return;
        }
        if (!menu || event.ctrlKey || event.metaKey || event.altKey) return;
        if (event.key === 'Escape') {event.preventDefault(); event.stopPropagation(); hide();}
        else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {event.preventDefault(); event.stopPropagation(); selected = (selected + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length; draw(); menu.children[selected]?.scrollIntoView({block:'nearest'});}
        else if (!event.shiftKey && (event.key === 'Tab' || event.key === 'Enter')) {event.preventDefault(); event.stopPropagation(); commit(selected);}
    }
    const start = () => {composing = true; hide();}, finish = () => {composing = false; void update();};
    const listeners = [['input', update], ['click', update], ['keydown', keydown], ['blur', hide], ['compositionstart', start], ['compositionend', finish]];
    for (const [type, listener] of listeners) input.addEventListener(type, listener);
    const onScroll = event => { if (!menu?.contains(event.target)) hide(); };
    doc.addEventListener('scroll', onScroll, true); window.addEventListener('resize', hide);
    const cleanup = () => {
        destroyed = true; hide(); for (const [type, listener] of listeners) input.removeEventListener(type, listener);
        doc.removeEventListener('scroll', onScroll, true); window.removeEventListener('resize', hide);
        for (const [name, value] of [['role', previous.role], ['aria-autocomplete', previous.autocomplete], ['aria-expanded', previous.expanded]])
            if (value === null) input.removeAttribute(name); else input.setAttribute(name, value);
        attached.delete(input);
    };
    attached.set(input, cleanup); return cleanup;
}
function attachNode(node) {
    for (const w of node.widgets ?? []) if (isPromptWidget(node, w.name) || ['value', 'text'].includes(w.name)) attachAutocomplete(w.inputEl ?? w.element, {native:true, eligible:() => isPromptWidget(node, w.name)});
    if (!node.__rsAutocompleteRemoval) {
        node.__rsAutocompleteRemoval = true; const remove = node.onRemoved;
        node.onRemoved = function(...args) {for (const w of this.widgets ?? []) attached.get(w.inputEl ?? w.element)?.(); return remove?.apply(this, args);};
    }
}
app.registerExtension({name:'RS.MultiCharacter.PromptAutocomplete',
    setup() {
        const style = document.createElement('link'); style.rel = 'stylesheet'; style.href = new URL('./prompt_autocomplete.css', import.meta.url).href; document.head.append(style);
        app.ui?.settings?.addSetting({id:'RS.MultiCharacter.Autocomplete', name:'RS: Built-in prompt autocomplete', type:'boolean', defaultValue:true, onChange:value => {enabled = value;}});
        for (const node of app.graph?._nodes ?? []) attachNode(node);
    },
    nodeCreated(node) {attachNode(node);},
    loadedGraphNode(node) {attachNode(node);},
});
