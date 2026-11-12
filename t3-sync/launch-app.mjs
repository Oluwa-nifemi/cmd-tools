#!/usr/bin/env node
// A separate process session owns the GUI app, not the shell/agent that requested it.
import { spawn } from "node:child_process";
import { mkdirSync, openSync, closeSync } from "node:fs";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";

const copy = process.argv[2];
if (!['personal', 'draft'].includes(copy)) {
  console.error('Usage: launch-app.mjs <personal|draft> [--dry-run]');
  process.exit(2);
}
const dryRun = process.argv.includes('--dry-run');
const root = '/Users/nifemi/Documents/work/t3code';
const local = copy === 'personal'
  ? '/Users/nifemi/Documents/work/opencodex/local/t3code-personal'
  : '/Users/nifemi/Documents/Codex/2026-11-03/for-some-reason-computer-use-doesnt/local/t3-draft';
const checkout = copy === 'personal' ? root : join(root, 'draft');
const name = `T3 Code (${copy === 'personal' ? 'Personal' : 'Draft'})`;
const vars = {
  T3CODE_HOME: join(local, 'profile'),
  T3CODE_DESKTOP_USER_DATA_DIR: join(local, 'profile', 'chromium'),
  T3CODE_DESKTOP_APP_NAME: name,
  T3CODE_DESKTOP_APP_USER_MODEL_ID: `com.nifemi.t3code.${copy}`,
  T3CODE_DESKTOP_ZOOM_FACTOR: '1.1',
  T3CODE_PORT: copy === 'personal' ? '3773' : '3873',
  T3CODE_TELEMETRY_ENABLED: 'false',
  T3CODE_DISABLE_AUTO_UPDATE: 'true',
  ...(copy === 'draft' ? {
    T3CODE_DESKTOP_PROTOCOL_SCHEME: 't3code-draft',
    T3CODE_DESKTOP_MAC_ICON_PNG: join(local, 'icon', 'draft-macos-1024.png'),
  } : {}),
};
// Runtime selection reads the app name. Clear the other copy's inherited settings
// and agent-only routing context before resolving and starting its bundle.
for (const key of Object.keys(process.env)) {
  if (key.startsWith('T3CODE_') || key.startsWith('VITE_') || key.startsWith('T3_') || key.startsWith('PI_')) delete process.env[key];
}
delete process.env.ELECTRON_RUN_AS_NODE;
Object.assign(process.env, vars);
const { resolveElectronLaunchCommand, desktopDir } = await import(
  pathToFileURL(join(checkout, 'apps/desktop/scripts/electron-launcher.mjs'))
);
const command = resolveElectronLaunchCommand([join(desktopDir, 'dist-electron/main.cjs')]);
const app = dirname(dirname(dirname(command.electronPath)));
const log = join(local, 'logs', `${copy}.log`);
if (dryRun) {
  console.log(JSON.stringify({ copy, app, checkout, profile: vars.T3CODE_HOME, log,
    owner: 'independent process session', terminalWindow: false }, null, 2));
} else {
  mkdirSync(dirname(log), { recursive: true, mode: 0o700 });
  const output = openSync(log, 'a', 0o600);
  let child;
  try {
    // detached creates a new session/process group; file-backed stdio removes the
    // controlling terminal. unref then lets this short launcher exit independently.
    child = spawn(command.electronPath, command.args, {
      cwd: checkout, env: process.env, detached: true, stdio: ['ignore', output, output],
    });
  } finally {
    closeSync(output);
  }
  child.once('error', error => { console.error(error.message); process.exitCode = 1; });
  child.once('spawn', () => {
    console.log(`${name} opened independently. PID: ${child.pid}. Logs: ${log}`);
    child.unref();
  });
}
