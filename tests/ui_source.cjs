const fs = require('fs');
module.exports = function uiSource(path) {
  let source = fs.readFileSync(path, 'utf8');
  if (source.includes('from "./i18n.js"')) {
    const strip = text => text.replace(/^import[^\n]*\n/gm, '').replaceAll('export const', 'const').replaceAll('export function', 'function');
    source = strip(fs.readFileSync('web/zh_messages.js', 'utf8')) + '\n' + strip(fs.readFileSync('web/i18n.js', 'utf8')) + '\n' + source;
  }
  return source;
};
