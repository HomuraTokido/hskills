// Claude Code PreToolUse hook: every `git push` Claude runs through Bash or PowerShell waits for
// 「マスター」's click. Claude has the permission to push but may not use it on its own
// (rules/hosts/claude.md, 2026-10-22); this hook makes the app ask instead of letting it through.
// Anything else passes untouched: no output, exit 0.
//
// A repository whose own rules let Claude push on its own judgment (project rules outrank the global
// one) carries a local switch, read here and nowhere else:
//   git -C <repo> config --local claude.allowPush true
// It lives in that repository's .git/config, on this machine only. A push goes through without a
// click only when every push in the command targets a repository with the switch on; a target the
// hook cannot tell, or cannot read, is asked about.
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

if (process.argv.slice(2).some(arg => arg === '--help' || arg === '-h')) {
  console.log('Usage: node confirm-push.mjs [--help|-h]\nRead a PreToolUse JSON payload from stdin; request approval for recognized pushes.\nOutput language: HSKILLS_LANG=en (default) or zh.');
  process.exit(0);
}

const ARG = String.raw`(?:"[^"]*"|'[^']*'|[^\s;&|]+)`;
// `git`, then any global options (-C <dir>, -c <k=v>, --git-dir=..., --no-pager), then the `push`
// subcommand. A commit message that merely contains the word "push" does not match.
const PUSH = new RegExp(String.raw`(?:^|[\s;&|(\`])git(?:\.exe)?((?:\s+-[Cc]\s+${ARG}|\s+--?[\w-]+(?:=${ARG})?)*)\s+push\b`, 'g');
// gh commands that push on their own: `gh repo create ... --push` and `gh pr create` (which pushes the
// branch first when it is not on the remote). Their target cannot be told from the command, so they
// are always asked about. Added 2026-10-27 after a `gh repo create --push` went through
// on a machine that had no hook at all.
const GH_PUSH = /(?:^|[\s;&|(`])gh(?:\.exe)?\s+(?:repo\s+create\b[^;&|\n]*\s--push\b|pr\s+create\b)/;

// Text that is data, not a command: a quoted string that is not handed to a shell to run, and a
// heredoc body. A test file containing 'git push*' or a commit message saying "git push" is not a
// push; before 2026-10-23 every such command stopped Claude until 「マスター」 clicked through (36
// asks in the log, nearly all of them strings). Quoted text after -c / -Command / /c / eval is
// still a command and is still checked.
const RUNS_QUOTED = /(?:\s-c|\s-Command|\s-command|\s\/c|\s\/C|(?:^|[\s;&|])eval)\s*$/;
function neutralize(text) {
  return text.replace(/\bgit\b/g, 'g_t').replace(/\bgh\b/g, 'g_h');
}
function visibleCommand(command) {
  let text = command.replace(/(<<-?\s*(['"]?)(\w+)\2[^\n]*\n)([\s\S]*?)(\n\3[ \t]*(?:\n|$))/g, (_m, head, _q, _tag, body, tail) => head + neutralize(body) + tail);
  let out = '';
  for (let index = 0; index < text.length; index += 1) {
    const ch = text[index];
    if (ch !== '"' && ch !== "'") { out += ch; continue; }
    let end = index + 1;
    while (end < text.length && text[end] !== ch) end += ch === '"' && text[end] === '\\' ? 2 : 1;
    const inner = text.slice(index + 1, end);
    out += ch + (RUNS_QUOTED.test(out) ? ' ' + inner : neutralize(inner)) + (end < text.length ? ch : '');
    index = end;
  }
  return out;
}
const DASH_C = new RegExp(String.raw`\s-C\s+(${ARG})`, 'g');
// A change of directory earlier in the same command: cd, pushd, Set-Location (with or without -Path).
const CD = new RegExp(String.raw`(?:^|[\s;&|(])(?:cd|pushd|Set-Location|sl)(?:\s+-(?:Path|LiteralPath))?\s+(${ARG})`, 'gi');

function unquote(text) {
  return text.replace(/^(["'])(.*)\1$/, '$2');
}

// A path as the shell would have seen it, made into one Windows git understands.
function localPath(text, base) {
  let p = unquote(text);
  if (p === '~' || p.startsWith('~/') || p.startsWith('~\\')) p = path.join(os.homedir(), p.slice(1));
  const msys = /^\/([a-zA-Z])(\/|$)/.exec(p);
  if (msys && process.platform === 'win32') p = `${msys[1]}:/${p.slice(3)}`;
  return path.resolve(base, p);
}

// The directory each `git push` in the command acts on, or null where it cannot be told.
function pushTargets(rawCommand, cwd) {
  const targets = [];
  const command = visibleCommand(rawCommand);
  for (const match of command.matchAll(PUSH)) {
    let dir = cwd || null;
    for (const cd of command.slice(0, match.index).matchAll(CD)) dir = dir ? localPath(cd[1], dir) : null;
    for (const c of (match[1] ?? '').matchAll(DASH_C)) dir = dir ? localPath(c[1], dir) : null;
    targets.push(dir);
  }
  return targets;
}

function allowsPush(dir) {
  if (!dir) return false;
  try {
    const value = execFileSync('git', ['-C', dir, 'config', '--get', 'claude.allowPush'], {
      encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 5000, windowsHide: true,
    });
    return value.trim().toLowerCase() === 'true';
  } catch {
    return false;
  }
}

function log(input, decision, command) {
  try {
    fs.appendFileSync(new URL('./confirm-push.log', import.meta.url), `${new Date().toISOString()}\t${input.session_id ?? ''}\t${decision}\t${command.replace(/\s+/g, ' ').slice(0, 200)}\n`);
  } catch {}
}

function main() {
  let input = {};
  try {
    input = JSON.parse(fs.readFileSync(0, 'utf8') || '{}');
  } catch {
    return;
  }
  if (!['Bash', 'PowerShell'].includes(input.tool_name)) return;
  const command = String(input.tool_input?.command ?? '');
  const targets = pushTargets(command, input.cwd);
  if (GH_PUSH.test(visibleCommand(command))) targets.push(null);
  if (!targets.length) return;
  if (targets.every(allowsPush)) {
    log(input, 'allowed (claude.allowPush)', command);
    return;
  }
  log(input, 'asked', command);
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'ask',
      permissionDecisionReason: process.env.HSKILLS_LANG === 'zh'
        ? `push 要「マスター」点头才能跑：${command.slice(0, 200)}`
        : `Push requires the user's approval: ${command.slice(0, 200)}`,
    },
  }));
}

main();
