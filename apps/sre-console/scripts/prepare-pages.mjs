import { cpSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const output = join(root, 'dist');
let sourceHtml = readFileSync(join(root, 'index.html'), 'utf8');
const releaseSha = process.env.RELEASE_SHA || '';
if (!/^[0-9a-f]{40}$/.test(releaseSha)) {
  throw new Error('RELEASE_SHA must be a full Git commit hash');
}
const stylesheet = 'href="dist/assets/styles.css"';
if (!sourceHtml.includes(stylesheet)) {
  throw new Error('Console stylesheet path changed; review Pages build mapping');
}

mkdirSync(output, { recursive: true });
for (const tab of ['realtime', 'cluster', 'workload', 'gitops', 'gates']) {
  const placeholder = '<!-- loaded via fetch in app.js -->';
  if (!sourceHtml.includes(placeholder)) {
    throw new Error(`Missing placeholder for ${tab} tab`);
  }
  const content = readFileSync(join(root, 'tabs', `${tab}.html`), 'utf8');
  sourceHtml = sourceHtml.replace(placeholder, () => content);
}
writeFileSync(
  join(output, 'index.html'),
  sourceHtml.replace(stylesheet, 'href="assets/styles.css"').replace('__RELEASE_SHA__', releaseSha),
);
cpSync(join(root, 'tabs'), join(output, 'tabs'), { recursive: true });
cpSync(join(root, 'datafeed.js'), join(output, 'datafeed.js'));
cpSync(join(root, 'styles.css'), join(output, 'styles.css'));
