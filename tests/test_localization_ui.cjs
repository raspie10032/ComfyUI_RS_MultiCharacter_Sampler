// SPDX-License-Identifier: GPL-3.0-only
const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('node:assert/strict');
const strip = source => source.replace(/^import[^\n]*\n/gm, '').replaceAll('export const', 'var').replaceAll('export function', 'function');
const sandbox = {};
vm.runInNewContext(strip(fs.readFileSync('web/zh_messages.js', 'utf8')) + '\n' + strip(fs.readFileSync('web/i18n.js', 'utf8')), sandbox);
const {chineseLocale, chineseText, zhMessages} = sandbox;
for (const locale of ['zh', 'zh-CN', 'zh_cn', 'zh-Hans', 'zh-SG']) assert.equal(chineseLocale(locale), 'zh');
for (const locale of ['zh-TW', 'zh_tw', 'zh-Hant', 'zh-Hant-HK', 'zh-HK', 'zh-MO']) assert.equal(chineseLocale(locale), 'zh-TW');
for (const locale of ['en', 'ko', 'ja', 'fr', 'zhang']) assert.equal(chineseLocale(locale), null);
assert.equal(chineseText('Unknown file.safetensors', 'zh-TW'), 'Unknown file.safetensors');
assert.equal(chineseText('Open mask canvas', 'ko'), 'Open mask canvas');
assert.equal(chineseText('Character 7 · 320px · strength 0.85', 'zh-TW'), '角色 7 · 320px · 強度 0.85');
const vars = text => [...text.matchAll(/\{(\d+)\}/g)].map(m => m[1]).sort();
for (const [english, translations] of Object.entries(zhMessages)) {
  assert.equal(translations.length, 2);
  for (const [i, locale] of ['zh','zh-TW'].entries()) {
    assert.ok(translations[i].trim(), `${locale}: ${english}`);
    assert.doesNotMatch(translations[i], /[\uac00-\ud7af\u3041-\u3096\u30a1-\u30fa]/u);
    assert.deepEqual(vars(translations[i]), vars(english), `${locale}: placeholder loss: ${english}`);
    const rendered = english.replace(/\{\d+\}/g, m => `value.${m.slice(1,-1)} [1]+$`);
    const expected = translations[i].replace(/\{\d+\}/g, m => `value.${m.slice(1,-1)} [1]+$`);
    assert.equal(chineseText(rendered, locale), expected);
  }
}
// Catch untranslated static UI labels as new controls are added.
for (const file of ['node_help','mask_drawing','position_editor','pose_masks','pose3d']) {
  const source = fs.readFileSync(`web/${file}.js`, 'utf8');
  for (const match of source.matchAll(/\b(?:add|text|label)\(\s*((?:"(?:[^"\\]|\\.)*")|(?:'(?:[^'\\]|\\.)*'))/g)) {
    const english = vm.runInNewContext(match[1]);
    if (!/[a-z]/i.test(english)) continue;
    assert.ok(Object.hasOwn(zhMessages, english), `${file}: untranslated label ${english}`);
  }
}
const base = JSON.parse(fs.readFileSync('locales/ko/nodeDefs.json','utf8'));
const covers = (expected, actual, key) => {
  for (const [name,value] of Object.entries(expected)) {
    assert.ok(Object.hasOwn(actual,name), `${key}.${name}: missing translation`);
    if (value && typeof value === 'object') covers(value,actual[name],`${key}.${name}`);
    else assert.equal(typeof actual[name],typeof value,`${key}.${name}`);
  }
};
for (const locale of ['zh','zh-TW']) {
  const catalog = JSON.parse(fs.readFileSync(`locales/${locale}/nodeDefs.json`,'utf8'));
  covers(base, catalog, locale);
  assert.equal(Object.keys(catalog).length, Object.keys(base).length);
  for (const [id, def] of Object.entries(catalog)) {
    assert.match(def.display_name, /[\u4e00-\u9fff]/u, id);
    assert.doesNotMatch(JSON.stringify(def), /[\uac00-\ud7af\u3041-\u3096\u30a1-\u30fa]/u, id);
  }
  for (const preset of JSON.parse(fs.readFileSync('web/model_presets.json','utf8'))) {
    assert.ok(preset.label[locale] && preset.note[locale], `${locale}: ${preset.id}`);
  }
}
// Both full READMEs retain working local links and literal technical IDs.
for (const file of ['README.zh-CN.md','README.zh-TW.md']) {
  const text = fs.readFileSync(file,'utf8');
  for (const match of text.matchAll(/\]\(([^)]+)\)/g)) {
    if (/^(https?:|#)/.test(match[1])) continue;
    assert.ok(fs.existsSync(path.resolve(path.dirname(file),match[1].split('#')[0])), `${file}: broken link ${match[1]}`);
  }
  for (const term of ['moss_native','regional','character_pipe','use_image_settings','RS_MC_TEST_COMFYUI']) assert.ok(text.includes(term), `${file}: missing ${term}`);
  assert.equal((text.match(/^## /gm)??[]).length, (fs.readFileSync('README.md','utf8').match(/^## /gm)??[]).length);
}
console.log(`Chinese: ${Object.keys(base).length} nodes, ${Object.keys(zhMessages).length} messages, locale aliases, placeholders, 18 presets, readable panels and both README links passed`);
