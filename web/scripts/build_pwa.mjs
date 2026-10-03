import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dist = path.join(root, 'dist');
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
async function walk(directory, prefix = '') {
  const files = [];
  for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
    const relative = prefix + entry.name;
    if (entry.isDirectory())
      files.push(...(await walk(path.join(directory, entry.name), relative + '/')));
    else if (entry.isFile() && relative !== 'sw.js') files.push(relative);
  }
  return files.sort();
}
const resources = [];
for (const name of await walk(dist))
  resources.push({ path: name, sha256: hash(await fs.readFile(path.join(dist, name))) });
if (!resources.some((file) => file.path === 'runtime/manifest.json'))
  throw Error('Prepare the Python runtime before building the PWA');
const source = await fs.readFile(path.join(root, 'scripts/service-worker.js'), 'utf8');
const build = hash(JSON.stringify(resources) + source);
await fs.writeFile(
  path.join(dist, 'sw.js'),
  `const BUILD_ID = ${JSON.stringify(build)};\nconst RESOURCES = ${JSON.stringify(resources)};\n${source}`,
);
console.log(`PWA: ${resources.length} static assets, atomic cache ${build.slice(0, 12)}`);
