#!/usr/bin/env python3
"""Stamp metadata.verified / metadata.sources into a skill's frontmatter.

Usage: stamp.py SKILL --at YYYY-MM-DD [--by human:<owner> --human-confirmed | --by ai:<model>]
                [--source "resource|id|title"]... [--root DIR]

`by: human:...` means she looked at this very version herself and said yes.
An agent stamping it has to add --human-confirmed, a deliberate extra word:
add it only when she confirmed this version in the conversation. A version
only an agent checked is stamped `--by ai:<model>` and needs no flag.

Replaces `verified` in place (or inserts it right after `metadata:`) and
appends `sources` entries to the end of the existing list (or creates the list
right after `verified`), creating `metadata:` when absent. Text-level edit: the
rest of the frontmatter (folded descriptions, host keys) is left byte-for-byte.
"""
import os
import pathlib
import re
import sys


def find_root(start):
    p = start
    while p != p.parent:
        if (p / "skills").is_dir():
            return p
        p = p.parent
    raise SystemExit("找不到 skills/ 目录，用 --root 指定")


def _yaml_str(value):
    """Double-quote a scalar so colons, hashes and quotes inside it stay literal."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _block_end(lines, start, indent, seq=False):
    """Index just past the block headed by lines[start]: the following lines
    indented deeper than `indent`, plus `- ` items at `indent` when seq (YAML's
    compact list style). Blank and comment lines count only inside the block."""
    end = start + 1
    for i in range(start + 1, len(lines)):
        s = lines[i]
        if not s.strip() or s.lstrip().startswith("#"):
            continue
        if _indent(s) > indent or (seq and _indent(s) == indent and s.lstrip(" ").startswith("-")):
            end = i + 1
        else:
            break
    return end


def _child(lines, head, key):
    """Line index of `  key:` directly under the `metadata:` line at head, or None."""
    for i in range(head + 1, _block_end(lines, head, 0)):
        if re.match(rf"  {key}:(?=\s)", lines[i]):
            return i
    return None


def _source_lines(sources, indent):
    pad = " " * indent
    out = []
    for s in sources:
        parts = (s.split("|") + ["", ""])[:3]
        out.append(f"{pad}- resource: {_yaml_str(parts[0])}\n")
        if parts[1]:
            out.append(f"{pad}  id: {_yaml_str(parts[1])}\n")
        if parts[2]:
            out.append(f"{pad}  title: {_yaml_str(parts[2])}\n")
    return out


def main(argv):
    if not argv or argv[0].startswith("--"):
        raise SystemExit(__doc__)
    name = argv[0]
    by = argv[argv.index("--by") + 1] if "--by" in argv else os.environ.get("HSKILLS_VERIFIER", "human:owner")
    if by.startswith("human:") and "--human-confirmed" not in argv:
        raise SystemExit(
            f"{name}: 没盖章。by: {by} 的意思是「ta本人看过这一版并点了头」。"
            "ta在对话里明确确认过这一版，才加 --human-confirmed 再跑一次；"
            "只是 agent 自己核过的，改用 --by ai:<模型名>（例如 ai:claude-opus-5-5），不用加这个参数。"
        )
    at = argv[argv.index("--at") + 1]
    sources = [argv[i + 1] for i, a in enumerate(argv) if a == "--source"]
    root = pathlib.Path(argv[argv.index("--root") + 1]) if "--root" in argv else find_root(pathlib.Path(__file__).resolve())
    p = root / "skills" / name / "SKILL.md"
    raw = p.read_bytes()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")
    m = re.match(r"^---\n(.*?\n)---\n", text, re.S)
    if not m:
        raise SystemExit(f"{name}: 没有 frontmatter")
    lines = m.group(1).splitlines(keepends=True)
    verified = ["  verified:\n", f"    by: {by}\n", f"    at: {at}\n"]
    head = next((i for i, l in enumerate(lines) if re.match(r"metadata:(?=\s)", l)), None)
    if head is None:
        lines += ["metadata:\n"] + verified
        if sources:
            lines += ["  sources:\n"] + _source_lines(sources, 4)
    else:
        if not re.fullmatch(r"metadata:[ \t]*(#.*)?\n", lines[head]):
            raise SystemExit(f"{name}: metadata 是行内形式，手工处理")
        v = _child(lines, head, "verified")
        if v is None:
            lines[head + 1:head + 1] = verified
        else:
            lines[v:_block_end(lines, v, 2)] = verified
        if sources:
            s = _child(lines, head, "sources")
            if s is None:
                pos = _block_end(lines, _child(lines, head, "verified"), 2)
                lines[pos:pos] = ["  sources:\n"] + _source_lines(sources, 4)
            elif not re.fullmatch(r"  sources:[ \t]*(#.*)?\n", lines[s]):
                raise SystemExit(f"{name}: metadata.sources 是行内形式，手工处理")
            else:
                # append after the last existing entry, at the indent the list already uses
                end = _block_end(lines, s, 2, seq=True)
                items = [l for l in lines[s + 1:end] if l.lstrip(" ").startswith("-")]
                lines[end:end] = _source_lines(sources, _indent(items[0]) if items else 4)
    out = "---\n" + "".join(lines) + "---\n" + text[m.end():]
    p.write_bytes(out.replace("\n", "\r\n").encode("utf-8") if crlf else out.encode("utf-8"))
    print(f"{name}: stamped verified {by} {at}, {len(sources)} source(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
