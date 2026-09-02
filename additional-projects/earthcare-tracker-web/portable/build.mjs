import { execFileSync } from 'node:child_process';
import { readFile, writeFile, mkdir, readdir, rm } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const project = resolve(here, '..');
const output = resolve(project, '..', '..', 'outputs', 'EarthCARE_ATLID_Portable_v2.html');
const stableOutput = resolve(project, '..', '..', 'outputs', 'EarthCARE_ATLID_Portable.html');
const pnpmDirectory = resolve(project, 'node_modules', '.pnpm');
const template = await readFile(resolve(here, 'template.html'), 'utf8');
const temporaryIndex = resolve(here, 'index.html');
const portableDist = resolve(project, 'portable-dist');
await writeFile(temporaryIndex, template.replace('<script>__PORTABLE_SCRIPT__</script>', '<script type="module" src="./entry.ts"></script>'), 'utf8');
const vitePackage = (await readdir(pnpmDirectory)).find((name) => /^vite@/.test(name));
if (!vitePackage) throw new Error('The project Vite package was not found.');
const viteBin = resolve(pnpmDirectory, vitePackage, 'node_modules', 'vite', 'bin', 'vite.js');
execFileSync(process.execPath, [viteBin, 'build', 'portable', '--config=portable/vite.config.mjs', '--base=./', '--outDir=../portable-dist', '--emptyOutDir'], { cwd: project, stdio: 'inherit' });
let builtHtml = await readFile(resolve(portableDist, 'index.html'), 'utf8');
const scriptMatch = builtHtml.match(/<script[^>]+src="\.\/assets\/([^"]+\.js)"[^>]*><\/script>/);
if (!scriptMatch) throw new Error('The portable JavaScript bundle was not found in the Vite output.');
const script = (await readFile(resolve(portableDist, 'assets', scriptMatch[1]), 'utf8')).replaceAll('</script', '<\\/script');
builtHtml = builtHtml.replace(scriptMatch[0], '');
if (!builtHtml.includes('</body>')) throw new Error('The portable HTML body closing tag was not found.');
builtHtml = builtHtml.replace('</body>', `<script>${script}</script>\n</body>`);
if (builtHtml.lastIndexOf('<script>') < builtHtml.indexOf('<body')) {
  throw new Error('The portable JavaScript bundle must execute after the interface markup.');
}
await mkdir(dirname(output), { recursive: true });
await writeFile(output, builtHtml, 'utf8');
await writeFile(stableOutput, builtHtml, 'utf8');
await rm(temporaryIndex, { force: true });
await rm(portableDist, { recursive: true, force: true });
console.log(output);
