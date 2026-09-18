import { readdir } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';

const root = resolve(import.meta.dirname, '..');
const args = process.argv.slice(2);

function option(name, fallback) {
  const inline = args.find(argument => argument.startsWith(`${name}=`));
  if (inline) return inline.slice(name.length + 1);
  const index = args.indexOf(name);
  return index >= 0 && args[index + 1] ? args[index + 1] : fallback;
}

// npm can consume the --count flag on Windows and forward only its value.
// Accept both `--count 5`, `--count=5`, and the forwarded positional `5`.
const positionalCount = args.find(argument => /^\d+$/.test(argument));
const count = Number(option('--count', positionalCount || '1'));
const timeoutSeconds = Number(option('--timeout-seconds', '300'));
const suppliedConfigDir = args.includes('--config-dir');
const configDir = resolve(root, option('--config-dir', 'data_pipeline/examples'));

if (!Number.isInteger(count) || count < 1) {
  console.error('--count must be a positive integer');
  process.exit(1);
}
if (!Number.isInteger(timeoutSeconds) || timeoutSeconds < 1) {
  console.error('--timeout-seconds must be a positive integer');
  process.exit(1);
}

const deadline = Date.now() + timeoutSeconds * 1000;

function remainingTimeout() {
  const remaining = deadline - Date.now();
  if (remaining <= 0) {
    console.error(`Candidate pipeline timed out after ${timeoutSeconds} seconds.`);
    process.exit(124);
  }
  return remaining;
}

function handleTimeout(result) {
  if (result.error?.code === 'ETIMEDOUT' || result.signal) {
    console.error(`Candidate pipeline timed out after ${timeoutSeconds} seconds.`);
    process.exit(124);
  }
}

function run(command, commandArgs, options = {}) {
  const result = spawnSync(command, commandArgs, {
    cwd: root,
    stdio: 'inherit',
    shell: process.platform === 'win32',
    timeout: remainingTimeout(),
    ...options,
  });
  handleTimeout(result);
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status || 1);
}

function runCapture(command, commandArgs) {
  const result = spawnSync(command, commandArgs, {
    cwd: root,
    encoding: 'utf8',
    shell: process.platform === 'win32',
    timeout: remainingTimeout(),
  });
  handleTimeout(result);
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  return result;
}

console.log('Starting local Postgres...');
console.log(`Candidate target: ${count}`);
console.log(`Pipeline timeout: ${timeoutSeconds} seconds`);
run('docker', ['compose', 'up', '-d', 'postgres']);

let migrated = false;
for (let attempt = 1; attempt <= 12; attempt += 1) {
  const result = spawnSync('npm', ['run', 'db:migrate'], {
    cwd: root,
    stdio: 'inherit',
    shell: process.platform === 'win32',
  });
  if (result.status === 0) {
    migrated = true;
    break;
  }
  if (attempt < 12) {
    console.log(`Database is not ready yet; retrying migration (${attempt}/11)...`);
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 1500);
  }
}
if (!migrated) process.exit(1);

console.log('Seeding local database...');
run('npm', ['run', 'db:seed']);

let accepted = 0;
async function processConfigs(activeConfigDir) {
  const configs = (await readdir(activeConfigDir, { withFileTypes: true }))
    .filter(entry => entry.isFile() && entry.name.endsWith('.json'))
    .map(entry => join(activeConfigDir, entry.name))
    .sort();
  for (const config of configs) {
    if (accepted >= count) break;
    console.log(`[pipeline] Ingesting candidate recipe: ${config}`);
    const ingest = runCapture('python', ['-m', 'data_pipeline.commands.ingest', config]);
    if (ingest.status !== 0) {
      console.log('[pipeline] Skipped: ingestion or exact-duplicate check failed');
      continue;
    }
    const match = `${ingest.stdout || ''}`.match(/Created candidate ([^\s]+)/);
    if (!match) {
      console.log('[pipeline] Skipped: ingestion did not return a candidate ID');
      continue;
    }
    const candidateId = match[1];
    console.log(`[pipeline] AI-reviewing candidate ${candidateId}`);
    const review = runCapture('python', ['-m', 'data_pipeline.commands.review', 'agent', candidateId]);
    if (review.status !== 0) {
      console.log('[pipeline] Skipped: AI review failed');
      continue;
    }
    let reviewData;
    try {
      reviewData = JSON.parse((review.stdout || '').trim());
    } catch {
      console.log('[pipeline] Skipped: AI review returned invalid JSON');
      continue;
    }
    if (reviewData.review?.verdict !== 'approve' || reviewData.review?.recommended_action !== 'approve') {
      console.log(`[pipeline] Rejected by AI review: ${reviewData.review?.verdict || 'unknown'}`);
      continue;
    }
    accepted += 1;
    console.log(`[pipeline] Accepted ${accepted}/${count}: ${candidateId}`);
  }
}

if (suppliedConfigDir) {
  await processConfigs(configDir);
} else {
  run('python', ['-u', '-m', 'data_pipeline.commands.produce', '--count', String(count)]);
  accepted = count;
}

if (accepted < count) {
  console.error(`Only ${accepted}/${count} candidates passed the full pipeline. No more distinct candidates were available in this discovery batch.`);
  process.exit(1);
}
console.log(`Created ${accepted} AI-approved candidate${accepted === 1 ? '' : 's'} in the local review database.`);
