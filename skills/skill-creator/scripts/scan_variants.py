#!/usr/bin/env python3
"""Find every on-disk copy of each HSkills skill and group them into variants.

Windows only: uses Everything's es.exe (must be on PATH, Everything running).

Usage: scan_variants.py [--skill NAME] [--all] [--summary] [--root DIR]
  --skill NAME  one skill, full detail (default: all skills, summary table)
  --all         include cache / backup / reference copies (hidden by default)
  --summary     force the table even with --skill
  --root DIR    repo root (default: walk up from this file)

Variants are grouped by a normalized hash (CRLF->LF, trailing whitespace
stripped, frontmatter dropped) so line-ending and description-only differences
do not count as separate versions. The raw md5 is shown too.
"""
import hashlib
import pathlib
import re
import subprocess
import sys

CATEGORIES = [  # first match wins; order matters
    ("cache", re.compile(r"\\\.codex\\plugins\\cache\\|\\\.cache\\|\\marketplace-cache\\|\\\.tmp\\|\\node_modules\\|\\plugins\\marketplaces\\", re.I)),
    ("backup", re.compile(r"backup|\\old-project\\|\\Downloads\\|\\.skill\.bak", re.I)),
    ("reference", re.compile(r"\\references?\\|\\vendor_imports\\|\\Program Files\\|\\WindowsApps\\", re.I)),
    ("worktree", re.compile(r"\\\.codex-worktrees\\|\\\.local\\share\\opencode\\worktree\\|local-agent-mode-sessions", re.I)),
    ("disabled", re.compile(r"\\disabled-skills\\", re.I)),
    ("source", re.compile(r"\\HSkills\\|\\skillshare\\|\\\.skillhub\\", re.I)),
    ("agent", re.compile(r"\\\.(agents|agent|claude|cc-switch|codex|config|grok|gemini|workbuddy|openclaw|zcode)\\|\\globals\\|\\AppData\\Local\\hermes\\skills\\", re.I)),
]
HIDDEN = {"cache", "backup", "reference"}


def find_root(start):
    p = start
    while p != p.parent:
        if (p / "skills").is_dir():
            return p
        p = p.parent
    raise SystemExit("找不到 skills/ 目录，用 --root 指定")


def categorize(path):
    for name, rx in CATEGORIES:
        if rx.search(path):
            return name
    return "other"


def es_copies(name):
    """All SKILL.md paths whose parent dir is exactly `name`."""
    out = subprocess.run(["es.exe", f"path:{name}", "wfn:SKILL.md", "-n", "500"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    suffix = f"\\{name}\\SKILL.md".lower()
    return [p for p in out.stdout.splitlines() if p.lower().endswith(suffix)]


def hashes(path):
    raw = pathlib.Path(path).read_bytes()
    text = raw.decode("utf-8", errors="replace").replace("\r\n", "\n")
    body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S)
    norm = "\n".join(l.rstrip() for l in body.splitlines()).strip()
    return hashlib.md5(raw).hexdigest()[:8], hashlib.md5(norm.encode()).hexdigest()[:8]


def scan(root, name, show_all):
    here = root / "skills" / name / "SKILL.md"
    _, here_norm = hashes(here)
    rows = []
    for p in es_copies(name):
        cat = categorize(p)
        if cat in HIDDEN and not show_all:
            continue
        try:
            raw, norm = hashes(p)
        except OSError:
            continue
        rows.append((norm, raw, cat, p))
    variants = {}
    for norm, raw, cat, p in rows:
        variants.setdefault(norm, []).append((raw, cat, p))
    return here_norm, variants


def main(argv):
    root = pathlib.Path(argv[argv.index("--root") + 1]) if "--root" in argv else find_root(pathlib.Path(__file__).resolve())
    show_all = "--all" in argv
    one = argv[argv.index("--skill") + 1] if "--skill" in argv else None
    names = [one] if one else sorted(d.name for d in (root / "skills").iterdir() if (d / "SKILL.md").is_file())
    detail = one and "--summary" not in argv
    if not detail:
        print(f"{'skill':28} {'copies':>6} {'variants':>8}  HSkills-variant-share  live-variants(agent/source/worktree)")
    for name in names:
        here_norm, variants = scan(root, name, show_all)
        copies = sum(len(v) for v in variants.values())
        share = len(variants.get(here_norm, []))
        live = {n for n, v in variants.items() if any(c in ("agent", "source", "worktree", "disabled", "other") for _, c, _ in v)}
        if detail:
            print(f"== {name}: {copies} copies, {len(variants)} variants (HSkills = {here_norm})")
            for norm, v in sorted(variants.items(), key=lambda kv: -len(kv[1])):
                tag = "  <- HSkills" if norm == here_norm else ""
                print(f"\n  variant {norm}  x{len(v)}{tag}")
                for raw, cat, p in sorted(v, key=lambda r: (r[1], r[2])):
                    print(f"    {raw} {cat:9} {p}")
        else:
            print(f"{name:28} {copies:6} {len(variants):8}  {share}/{copies:<20} {len(live)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
