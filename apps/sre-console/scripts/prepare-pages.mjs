import { cpSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { execFileSync } from 'node:child_process';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const output = join(root, 'dist');
const sourceHtml = readFileSync(join(root, 'index.html'), 'utf8');
const releaseSha = process.env.RELEASE_SHA || execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim();
if (!/^[0-9a-f]{40}$/.test(releaseSha)) {
  throw new Error('RELEASE_SHA must be a full Git commit hash');
}
const stylesheet = 'href="dist/assets/styles.css"';
if (!sourceHtml.includes(stylesheet)) {
  throw new Error('Console stylesheet path changed; review Pages build mapping');
}

mkdirSync(output, { recursive: true });
writeFileSync(
  join(output, 'index.html'),
  sourceHtml.replace(stylesheet, 'href="assets/styles.css"').replace('__RELEASE_SHA__', releaseSha),
);
cpSync(join(root, 'tabs'), join(output, 'tabs'), { recursive: true });
cpSync(join(root, 'datafeed.js'), join(output, 'datafeed.js'));
cpSync(join(root, 'styles.css'), join(output, 'styles.css'));
