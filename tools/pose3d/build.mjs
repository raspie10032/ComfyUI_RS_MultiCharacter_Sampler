import {readFile,writeFile} from 'node:fs/promises';
import {build} from 'esbuild';
await build({entryPoints:['../../web/pose3d/editor.mjs'],bundle:true,format:'esm',target:'es2022',minify:true,
    outfile:'../../web/pose3d/editor.bundle.mjs',legalComments:'eof',nodePaths:[new URL('./node_modules',import.meta.url).pathname]});

// Normalize insignificant shader trailing whitespace in the generated artifact.
const output=new URL('../../web/pose3d/editor.bundle.mjs',import.meta.url);
await writeFile(output,(await readFile(output,'utf8')).replace(/[ \t]+$/gm,''));
