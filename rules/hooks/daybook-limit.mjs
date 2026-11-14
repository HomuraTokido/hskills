// Claude Code SessionStart hook: measures ~/.claude/daybook.md and, once the book is past its
// limit, puts one plain-language note at the top of the session so Claude tells 「マスター」
// it is time to sort it. Under the limit it prints nothing and exits 0.
//
// The daybook is loaded into every session (rules/hosts/claude.md), so its length is paid every
// turn and dilutes the rules. The limit dates from 2026-10-25, a little tighter than core's
// "about 200 lines or 20KB into context at once", because this file is read every turn. It is
// size only: the 100-entry count was dropped on 2026-10-27 because 15KB is about 55 entries and
// always hit first. Measuring is left to this hook rather than to a rule: the moment the book
// grows long is the moment the model is least likely to notice.
//
// Source: HSkills rules/hooks/daybook-limit.mjs, copied to ~/.claude/hooks/ on install.
// For testing, a path given as the first argument is read instead of ~/.claude/daybook.md.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

if (process.argv.slice(2).some(arg => arg === '--help' || arg === '-h')) {
  console.log('Usage: node daybook-limit.mjs [PATH] [--help|-h]\nWarn when PATH (default: ~/.claude/daybook.md) exceeds 15 KB.\nOutput language: HSKILLS_LANG=en (default) or zh.');
  process.exit(0);
}

const MAX_KB = 15;

const file = process.argv[2] || path.join(os.homedir(), '.claude', 'daybook.md');

let text;
try {
  text = fs.readFileSync(file, 'utf8');
} catch {
  process.exit(0); // no daybook on this machine yet: nothing to say
}

const kb = Buffer.byteLength(text, 'utf8') / 1024;

if (kb <= MAX_KB) process.exit(0);

console.log(
  process.env.HSKILLS_LANG === 'zh'
    ? `daybook 过线了：${file} 现在 ${kb.toFixed(1)}KB，上限 ${MAX_KB}KB。` +
    `它每次开会话都整份读进上下文，越长越占地方。` +
    `在这次会话的第一条回复里告诉「マスター」，问ta要不要现在过一次账` +
    `（把条目分进 HSkills 的 rules/、Hwiki，或者留在原处过期）；ta说先不过，就照常干活，不再提。`
    : `Daybook exceeds its limit: ${file} is ${kb.toFixed(1)} KB; the limit is ${MAX_KB} KB. ` +
      'The entire file is loaded into context at every session start. In the first reply, tell the user ' +
      'and ask whether to review entries now (move them into HSkills rules/ or Hwiki, or leave them to expire). ' +
      'If the user postpones the review, continue working without further reminders.'
);
