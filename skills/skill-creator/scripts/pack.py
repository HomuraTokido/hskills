#!/usr/bin/env python3
"""claude.ai 是一个手动 target：只能在网页 Settings > Capabilities > Skills 传 zip，没有 CLI。
本脚本负责两件事：把 hotlist.md 里标了 web 的 skill 打成可上传的 zip；检查网页端那份是否已经落后。

  不带参数  只打印本说明，什么都不做
  --build   为每个 web skill 生成 build/web/<name>.zip（zip 内是 <name>/SKILL.md ... 的目录结构）
  --check   不打包，比对 Claude 桌面端缓存的账号 skill 副本和 HSkills，列出过期项。只读，仅 Windows。
  --out     zip 输出目录（默认 <root>/build/web）
  --root    仓库根（默认从本文件向上找）

网页端没有版本同步：更新方式是在网页上删掉旧的、传新的 zip。
"""
import argparse
import glob
import json
import os
import pathlib
import re
import sys
import zipfile

SKIP_DIRS = {"__pycache__", ".git", ".DS_Store"}
SKIP_SUFFIX = (".pyc",)


def find_root(start):
    p = pathlib.Path(start).resolve()
    for cand in [p, *p.parents]:
        if (cand / "hotlist.md").exists() and (cand / "skills").is_dir():
            return cand
    raise SystemExit("找不到仓库根（需要 hotlist.md 和 skills/），用 --root 指定")


def web_skills(root):
    """hotlist.md 中 web 列为 yes 的 skill 名（按表头定位 web 列，自动去重）。"""
    names = []
    seen = set()
    web_idx = None
    for line in (root / "hotlist.md").read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith("|"):
            web_idx = None
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells or set(cells[0]) <= {"-", ":"}:
            continue
        if cells[0] == "skill":
            web_idx = cells.index("web") if "web" in cells else None
            continue
        if web_idx is None or web_idx >= len(cells) or not cells[0]:
            continue
        if cells[web_idx].lower() == "yes" and cells[0] not in seen:
            seen.add(cells[0])
            names.append(cells[0])
    return names


def skill_files(skill_dir):
    for f in sorted(skill_dir.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(skill_dir)
        if any(part in SKIP_DIRS for part in rel.parts) or f.suffix in SKIP_SUFFIX:
            continue
        yield rel, f


def pack(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for name in web_skills(root):
        src = root / "skills" / name
        if not (src / "SKILL.md").exists():
            print(f"{name}: 跳过，skills/{name}/SKILL.md 不存在")
            continue
        target = out / f"{name}.zip"
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
            for rel, f in skill_files(src):
                z.write(f, f"{name}/{rel.as_posix()}")
        print(f"{name}: {target} ({target.stat().st_size} bytes)")


def desktop_cache():
    """Claude 桌面端把账号里启用的 skill 缓存成一个插件目录；取 manifest 最新的那份。"""
    base = pathlib.Path(os.environ.get("APPDATA", "")) / "Claude" / "local-agent-mode-sessions" / "skills-plugin"
    best = None
    for m in glob.glob(str(base / "*" / "*" / "manifest.json")):
        try:
            stamp = json.loads(pathlib.Path(m).read_text(encoding="utf-8")).get("lastUpdated", 0)
        except (OSError, ValueError):
            continue
        if best is None or stamp > best[0]:
            best = (stamp, pathlib.Path(m).parent)
    return best[1] if best else None


def norm(f):
    return f.read_bytes().replace(b"\r\n", b"\n")


def check(root):
    cache = desktop_cache()
    if cache is None:
        print("找不到 Claude 桌面端的账号 skill 缓存，无法比对")
        return 1
    stale = 0
    web = web_skills(root)
    for name in web:
        here = root / "skills" / name
        there = cache / "skills" / name
        if not there.exists():
            print(f"{name}: 网页端没有（未上传，或账号里关了）"); stale += 1
            continue
        a = {rel.as_posix(): f for rel, f in skill_files(here)}
        b = {rel.as_posix(): f for rel, f in skill_files(there)}
        diff = sorted(k for k in a.keys() & b.keys() if norm(a[k]) != norm(b[k]))
        only_a = sorted(a.keys() - b.keys())
        only_b = sorted(b.keys() - a.keys())
        if diff or only_a or only_b:
            stale += 1
            parts = []
            if diff:
                parts.append("改动 " + ", ".join(diff))
            if only_a:
                parts.append("网页端缺 " + ", ".join(only_a))
            if only_b:
                parts.append("网页端多 " + ", ".join(only_b))
            print(f"{name}: 过期（{'；'.join(parts)}）")
        else:
            print(f"{name}: ok")
    # 账号里「マスター」自己传的（creatorType user）却没标 web 的；Anthropic 自带的同名 skill 不算
    try:
        manifest = json.loads((cache / "manifest.json").read_text(encoding="utf-8"))
        mine = {s["name"] for s in manifest.get("skills", []) if s.get("creatorType") == "user"}
    except (OSError, ValueError, KeyError):
        mine = set()
    extra = sorted(n for n in mine if n not in web)
    if extra:
        print(f"网页端还有自己传的但没标 web 的：{', '.join(extra)}")
    print(f"缓存：{cache}")
    return 1 if stale else 0


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, f"pack.py: {message}。什么都没写；完整用法看 pack.py --help。\n")


def parse_args(argv):
    # 不带参数等同 --help：模型试探不熟的脚本时会不带参数或猜一个参数，不能因此打包
    # （2026-11-01：`--help` 原先不认，被当成默认的打包跑了）。
    parser = Parser(prog="pack.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true", help="为每个 web skill 生成 zip")
    mode.add_argument("--check", action="store_true", help="只读：列出网页端落后的 skill，仅 Windows")
    parser.add_argument("--out", type=pathlib.Path, help="zip 输出目录（默认 <root>/build/web）")
    parser.add_argument("--root", type=pathlib.Path, help="仓库根（默认从本文件向上找）")
    if not argv:
        parser.print_help()
        sys.exit(0)
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    root = args.root or find_root(__file__)
    if args.check:
        return check(root)
    pack(root, args.out or root / "build" / "web")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
