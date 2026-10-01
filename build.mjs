import {cp,mkdir,rm,readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {dirname,join} from 'node:path';
const root=dirname(fileURLToPath(import.meta.url));
const out=join(root,'dist');
await rm(out,{recursive:true,force:true});await mkdir(out,{recursive:true});
for(const name of ['index.html','styles.css','app.js','commerce.js','courses.js','foundations.js','manifest.json','sw.js','assets','teaching'])await cp(join(root,name),join(out,name),{recursive:true});
// Prevent probing a backend that is not deployed with this static build.
const script=await readFile(join(out,'app.js'),'utf8');
await writeFile(join(out,'app.js'),script.replace("async function api(path,options={}){", "async function api(path,options={}){throw new Error('This Vercel deployment uses browser-local learning. Account services require the academy backend.');"));
console.log('ETHAN LMS static build ready: dist/index.html, 120 courses, logo and all media packs.');
