#!/usr/bin/env python3
"""Lint HSkills skills against skills/skill-creator/SKILL.md.

Usage: lint_skills.py [--stats] [--index] [--write] [--root DIR]
  --stats   print line counts and description lengths, longest first
  --index   print INDEX.md derived from parent links
  --write   with --index, write INDEX.md to the repo root
  --root    repo root (default: walk up from this file to the dir containing skills/)
Exit code 1 when any error was found.

Two kinds of skills:
  own skills      frontmatter rules apply; metadata.verified / sources live in the file
  upstream skills a card exists at cards/<name>.md; the SKILL.md bytes belong upstream,
                  so description/metadata rules are skipped and instead the skill dir is
                  compared with the optional local clone when configured. Links on the card
                  join the link graph.
"""
import datetime
import pathlib
import re
import sys

if __name__ == "__main__" and any(arg in ("--help", "-h") for arg in sys.argv[1:]):
    print("Usage: lint_skills.py [--root DIR] [--stats] [--index] [--check|--write]\n"
          "  --root DIR  repository root (default: discover from this script)\n"
          "  --stats     print skill line counts and description lengths\n"
          "  --index     print the generated INDEX.md\n"
          "  --check     with --index, check freshness without writing\n"
          "  --write     with --index, write INDEX.md\n"
          "  --help, -h  show this help without linting")
    sys.exit(0)

try:
    import yaml
except ImportError:
    print("lint_skills.py: missing dependency PyYAML>=6.0. Install with: python -m pip install -r requirements.txt", file=sys.stderr)
    sys.exit(2)

HOST_KEYS = {"license", "allowed-tools", "compatibility", "user-invocable", "disable-model-invocation"}
KNOWN = {"name", "description", "metadata"} | HOST_KEYS
LINK_TYPES = {"parent", "related", "dispatch", "alternative"}
LINK_RE = re.compile(r"^- (\w+):\s*\[[^\]]*\]\(\.\./([^/)]+)/SKILL\.md\)")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
BODY_LINES_HINT = 500  # anthropic skill-creator: keep SKILL.md under 500 lines
CARD_KEYS = {"skill", "upstream", "path", "commit", "clone", "verified", "links", "ignore"}


def find_root(start):
    p = start
    while p != p.parent:
        if (p / "skills").is_dir():
            return p
        p = p.parent
    raise SystemExit("找不到 skills/ 目录，用 --root 指定")


def split_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return None, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        return {"__error__": str(e)}, text[m.end():]
    if not isinstance(fm, dict):
        return {"__error__": "frontmatter 不是映射"}, text[m.end():]
    return fm, text[m.end():]


def parse_links(body):
    links, in_sec = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            in_sec = line.strip() == "## Skill links"
            continue
        if in_sec:
            m = LINK_RE.match(line.strip())
            if m:
                links.append((m.group(1), m.group(2)))
    return links


def check_verified(v, out, where="metadata.verified"):
    for it in v if isinstance(v, list) else [v]:
        if not isinstance(it, dict) or "by" not in it or "at" not in it:
            out.append(("error", f"{where} 项需要 by 和 at"))
            continue
        try:
            datetime.date.fromisoformat(str(it["at"])[:10])
        except ValueError:
            out.append(("error", f"{where}.at 不是 ISO 日期: {it['at']}"))


def normalized(path):
    text = path.read_bytes().decode("utf-8", errors="replace").replace("\r\n", "\n")
    return "\n".join(l.rstrip() for l in text.splitlines()).strip()


def compare_dirs(ours, theirs, ignore=()):
    """Return a list of differences between two skill dirs, ignoring CRLF, trailing space, and `ignore` paths."""
    diffs = []
    ignore = set(ignore)

    def files(base):
        return {p.relative_to(base).as_posix() for p in base.rglob("*")
                if p.is_file() and ".git" not in p.relative_to(base).parts} - ignore

    ours_files, theirs_files = files(ours), files(theirs)
    for rel in sorted(ours_files - theirs_files):
        diffs.append(f"只在 HSkills: {rel}")
    for rel in sorted(theirs_files - ours_files):
        diffs.append(f"只在克隆: {rel}")
    for rel in sorted(ours_files & theirs_files):
        if normalized(ours / rel) != normalized(theirs / rel):
            diffs.append(f"内容不同: {rel}")
    return diffs


def load_cards(root):
    cards, issues = {}, []
    cards_dir = root / "cards"
    if not cards_dir.is_dir():
        return cards, issues
    for f in sorted(cards_dir.glob("*.md")):
        fm, _ = split_frontmatter(f.read_text(encoding="utf-8"))
        name = f.stem
        if fm is None or "__error__" in fm:
            issues.append(("error", f"cards/{f.name}: frontmatter 缺失或解析失败"))
            continue
        if fm.get("skill") != name:
            issues.append(("error", f"cards/{f.name}: skill 应为 {name}，实际 {fm.get('skill')!r}"))
        for k in ("upstream", "path", "commit"):
            if not fm.get(k):
                issues.append(("error", f"cards/{f.name}: 缺 {k}"))
        for k in fm:
            if k not in CARD_KEYS:
                issues.append(("warning", f"cards/{f.name}: 未知键 {k}"))
        if "verified" in fm:
            check_verified(fm["verified"], issues, where=f"cards/{f.name} verified")
        links = []
        for item in fm.get("links") or []:
            if not isinstance(item, dict) or "type" not in item or "target" not in item:
                issues.append(("error", f"cards/{f.name}: links 项需要 type 和 target"))
                continue
            links.append((str(item["type"]), str(item["target"])))
        cards[name] = {"fm": fm, "links": links, "file": f}
    return cards, issues


def lint_one(d, card):
    text = (d / "SKILL.md").read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    issues = []
    if fm is None:
        issues.append(("error", "没有 frontmatter"))
        fm = {}
    if "__error__" in fm:
        issues.append(("error", "frontmatter 解析失败: " + fm["__error__"]))
        fm = {}
    name = str(fm.get("name", "") or "")
    if name != d.name:
        issues.append(("error", f"name 应为 {d.name}，实际 {name!r}"))
    desc = str(fm.get("description", "") or "").strip()
    links = parse_links(body)
    if card is not None:
        # upstream skill: bytes belong upstream, compare with the clone instead
        c = card["fm"]
        clone_value = str(c.get("clone") or "").strip()
        if clone_value:
            clone = pathlib.Path(clone_value).expanduser() / str(c.get("path", ""))
            if not clone.is_dir():
                issues.append(("warning", f"上游克隆不在: {clone}"))
            else:
                for diff in compare_dirs(d, clone, ignore=[str(x) for x in (c.get("ignore") or [])]):
                    issues.append(("error", f"与上游克隆 {c.get('commit')} 不一致: {diff}"))
        if links:
            issues.append(("warning", "上游 skill 的文件里有 Skill links 段，应挪到 cards/"))
        links = links + card["links"]
        return {"desc": desc, "lines": len(text.splitlines()), "links": links, "issues": issues, "upstream": True}
    if name and (not NAME_RE.match(name) or len(name) > 64):
        issues.append(("error", "name 须为小写 kebab-case 且 64 字内"))
    if not desc:
        issues.append(("error", "缺 description"))
    else:
        if len(desc) > 1024:
            issues.append(("error", f"description {len(desc)} 字，宿主上限 1024"))
        if "<" in desc or ">" in desc:
            issues.append(("error", "description 不能含尖括号"))
        if desc.startswith("[TODO"):
            issues.append(("error", "description 是 TODO 占位符"))
    for k in fm:
        if k not in KNOWN:
            issues.append(("warning", f"未知顶层键 {k}"))
    meta = fm.get("metadata") or {}
    if isinstance(meta, dict):
        if "verified" in meta:
            check_verified(meta["verified"], issues)
        if "sources" in meta:
            src = meta["sources"]
            if not (isinstance(src, list) and all(isinstance(s, dict) and "resource" in s for s in src)):
                issues.append(("error", "metadata.sources 须为列表，每项含 resource"))
    if re.search(r"^\s*\[TODO:", body, re.M):
        issues.append(("error", "正文含 TODO 占位符"))
    n = len(text.splitlines())
    if n > BODY_LINES_HINT:
        issues.append(("warning", f"SKILL.md {n} 行，超过 {BODY_LINES_HINT}（anthropic 经验值）"))
    return {"desc": desc, "lines": n, "links": links, "issues": issues, "upstream": False}


def cross_check(skills):
    for name, s in skills.items():
        parents = [t for ty, t in s["links"] if ty == "parent"]
        if len(parents) > 1:
            s["issues"].append(("error", f"parent 多于一个: {parents}"))
        for ty, target in s["links"]:
            if ty == "child":
                s["issues"].append(("warning", f"遗留 child 链接 -> {target}，改为对方声明 parent"))
            elif ty not in LINK_TYPES:
                s["issues"].append(("warning", f"未知链接类型 {ty} -> {target}"))
            if target not in skills:
                s["issues"].append(("error", f"链接目标不存在: {target}"))
            elif ty == "related" and ("related", name) not in skills[target]["links"]:
                s["issues"].append(("warning", f"related 缺回链: {target} 未声明 related -> {name}"))


def _short_desc(text, limit=86):
    if len(text) <= limit:
        return text
    for sep in ("。", "；"):
        pos = text.find(sep)
        if 0 < pos <= limit:
            return text[: pos + 1]
    end = limit
    while end < len(text) and end < limit + 24 and text[end].isascii() and (text[end].isalnum() or text[end] in "_./:-"):
        end += 1
    if end < len(text) and text[end] in ("。", "；"):
        return text[: end + 1]
    return text[:end].rstrip(" 、，：,;—-(（“\"") + "…"


def build_index(skills):
    children = {n: [] for n in skills}
    for name, s in skills.items():
        for ty, t in s["links"]:
            if ty == "parent" and t in children:
                children[t].append(name)
    roots = [n for n, s in skills.items() if not any(ty == "parent" for ty, _ in s["links"])]
    lines = ["# INDEX", "", "由 skills/skill-creator/scripts/lint_skills.py --index 生成，不手改。", ""]

    def emit(n, depth):
        tag = "（上游）" if skills[n]["upstream"] else ""
        lines.append(f"{'  ' * depth}- [{n}](skills/{n}/SKILL.md){tag} — {_short_desc(skills[n]['desc'])}")
        for c in sorted(children[n]):
            emit(c, depth + 1)

    for n in sorted(roots):
        emit(n, 0)
    return "\n".join(lines) + "\n"


def parse_hotlist(root, skills):
    """Parse active hot skills from the '## 默认热层' section and validate all listed names."""
    path = root / "hotlist.md"
    issues = []
    hot = []
    if not path.is_file():
        return hot, [("error", "hotlist.md not found")]
    seen_active = set()
    section = None
    in_active = False
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("## "):
            section = s[3:].strip()
            in_active = section.startswith("默认热层")
            continue
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 3:
            continue
        name = cells[0]
        if name in ("skill", "") or set(name) <= {"-", ":"}:
            continue
        if name not in skills:
            issues.append(("error", f"hotlist.md references unknown skill: {name}"))
            continue
        if in_active:
            if name in seen_active:
                issues.append(("error", f"hotlist.md duplicates active skill: {name}"))
                continue
            seen_active.add(name)
            hot.append(name)
    return hot, issues


def build_skillignore(hot):
    lines = ["# 热冷过滤：默认全冷忽略（出厂 0 热，不侵入使用者原有习惯），仅反选 hotlist.md「默认热层」列出的热 skill。", "*"]
    lines.extend(f"!{name}" for name in hot)
    return "\n".join(lines) + "\n"


def sync_doc_counts(name, text, total, hot, cold):
    """Update hardcoded total/hot/cold skill counts in top-level docs."""
    rules_by_file = {
        "README.md": [
            (r"!\[(\d+) Hot · (\d+) Cold Split\]", f"![{hot} Hot · {cold} Cold Split]"),
            (r"badge/Context-(\d+)_Hot_%C2%B7_(\d+)_Cold-", f"badge/Context-{hot}_Hot_%C2%B7_{cold}_Cold-"),
            (r"(\*\*)(\d+)( daily-refined skill samples\*\*)", rf"\g<1>{total}\g<3>"),
            (r"(Currently )(\d+)( hot / )", rf"\g<1>{hot}\g<3>"),
            (r"( hot / )(\d+)( cold via `skills/\.skillignore`)", rf"\g<1>{cold}\g<3>"),
            (r"(## Repository layout: three layers and )(\d+)( reference samples)", rf"\g<1>{total}\g<3>"),
            (r"(currently enables )(\d+)( hot skill)", rf"\g<1>{hot}\g<3>"),
            (r"(with )(\d+)( cold samples remaining)", rf"\g<1>{cold}\g<3>"),
        ],
        "README.zh-CN.md": [
            (r"!\[(\d+) 热 · (\d+) 冷分层\]", f"![{hot} 热 · {cold} 冷分层]"),
            (r"badge/上下文-(\d+)_热_%C2%B7_(\d+)_冷-", f"badge/上下文-{hot}_热_%C2%B7_{cold}_冷-"),
            (r"(\*\*)(\d+)( 个日常打磨的 skill 样本\*\*)", rf"\g<1>{total}\g<3>"),
            (r"(当前 )(\d+)( 热 / )", rf"\g<1>{hot}\g<3>"),
            (r"( 热 / )(\d+)( 冷（出厂默认全冷)", rf"\g<1>{cold}\g<3>"),
            (r"(## 仓库结构：三层内容与 )(\d+)( 个参考样本)", rf"\g<1>{total}\g<3>"),
            (r"(`\.skillignore` 启用 )(\d+)( 个热 skill)", rf"\g<1>{hot}\g<3>"),
            (r"(其余 )(\d+)( 个留在冷层)", rf"\g<1>{cold}\g<3>"),
        ],
        "AGENTS.md": [
            (r"(规则和 )(\d+)( 个 `skill` 是作者日常真实使用的生产样本)", rf"\g<1>{total}\g<3>"),
            (r"(当前配置 )(\d+)( 热 / )", rf"\g<1>{hot}\g<3>"),
            (r"( 热 / )(\d+)( 冷，不侵入原有习惯；)", rf"\g<1>{cold}\g<3>"),
        ],
    }
    out = text
    for pattern, repl in rules_by_file.get(name, []):
        out, n = re.subn(pattern, repl, out)
        if n == 0:
            raise ValueError(f"{name}: count pattern did not match: {pattern}")
    return out


def _sync_generated(root, skills, argv):
    """Build or verify INDEX.md, skills/.skillignore, and top-level doc counts."""
    errors = 0
    write = "--write" in argv
    check = "--check" in argv

    hot, hot_issues = parse_hotlist(root, skills)
    for level, msg in hot_issues:
        print(f"{level:7} {msg}")
        errors += level == "error"
    if hot_issues:
        return errors

    total = len(skills)
    cold = total - len(hot)
    targets = [
        ("INDEX.md", root / "INDEX.md", build_index(skills)),
        ("skills/.skillignore", root / "skills" / ".skillignore", build_skillignore(hot)),
    ]
    for doc_name in ("README.md", "README.zh-CN.md", "AGENTS.md"):
        doc_path = root / doc_name
        if doc_path.is_file():
            cur_doc = doc_path.read_text(encoding="utf-8")
            try:
                targets.append((doc_name, doc_path, sync_doc_counts(doc_name, cur_doc, total, len(hot), cold)))
            except ValueError as exc:
                print(f"error   {exc}")
                return errors + 1

    if not check and not write:
        print("\n" + targets[0][2])
        return errors

    for label, path, expected in targets:
        cur = path.read_text(encoding="utf-8").replace("\r\n", "\n") if path.exists() else None
        if cur == expected.replace("\r\n", "\n"):
            continue
        if check:
            print(f"error   {label} is out of date (run lint_skills.py --index --write)")
            errors += 1
        elif write:
            path.write_text(expected, encoding="utf-8", newline="\n")
            print(f"wrote {label}")
    return errors


def main(argv):
    root = pathlib.Path(argv[argv.index("--root") + 1]) if "--root" in argv else find_root(pathlib.Path(__file__).resolve())
    skills_dir = root / "skills"
    cards, card_issues = load_cards(root)
    skills = {d.name: lint_one(d, cards.get(d.name)) for d in sorted(skills_dir.iterdir()) if (d / "SKILL.md").is_file()}
    for name in cards:
        if name not in skills:
            card_issues.append(("error", f"cards/{name}.md 没有对应的 skills/{name}/"))
    cross_check(skills)
    errors = warnings = 0
    for level, msg in card_issues:
        print(f"{level:7} {msg}")
        errors += level == "error"
        warnings += level != "error"
    for name, s in skills.items():
        for level, msg in s["issues"]:
            print(f"{level:7} {name}: {msg}")
            errors += level == "error"
            warnings += level != "error"
    n_up = sum(1 for s in skills.values() if s["upstream"])
    print(f"\n{len(skills)} skills ({n_up} upstream with cards), {errors} errors, {warnings} warnings")
    if "--stats" in argv:
        print("\nlines  desc  skill")
        for n, s in sorted(skills.items(), key=lambda kv: -kv[1]["lines"]):
            print(f"{s['lines']:5}  {len(s['desc']):4}  {n}{'  (upstream)' if s['upstream'] else ''}")
    if "--index" in argv:
        errors += _sync_generated(root, skills, argv)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
