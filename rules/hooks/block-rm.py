#!/usr/bin/env python3
"""PreToolUse hook (Bash): refuse any command that runs rm.

「マスター」2026-10-27: 删除只用回收站，找不到非用 rm 不可的理由。
Splits the command at shell separators and looks at the word each segment
actually runs, past wrappers such as sudo, env, xargs and timeout, inside
`bash -c '...'`, and after `find -exec`. `git rm` is not blocked: git history
keeps what it removes.
"""
import json
import os
import re
import shlex
import sys

for stream in (sys.stdout, sys.stderr):
    if stream is not None and hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass

WRAPPERS = {"sudo", "doas", "command", "builtin", "exec", "env", "nice", "nohup",
            "time", "timeout", "xargs", "stdbuf", "ionice", "chrt", "setsid"}
SHELLS = {"sh", "bash", "dash", "zsh"}
SEPARATORS = {";", "&", "&&", "|", "||", "(", ")", "\n", "|&"}
# What to use instead, per platform; the hook is installed only on Linux and macOS.
TRASH_HINT = {
    "darwin": "要删的东西改用 trash <路径>（系统自带的 /usr/bin/trash），进废纸篓，访达里能放回原处；",
    "linux": "要删的东西改用 gio trash <路径>，进回收站，Dolphin 里能还原；"
             "/tmp 等跨挂载点路径 gio trash 不支持时，移进 ~/.local/share/Trash/files/ 并写入同名 ~/.local/share/Trash/info/<name>.trashinfo，",
}


def is_rm(word):
    return os.path.basename(word.lstrip("\\")) == "rm"


def runs_rm(tokens):
    i = 0
    while i < len(tokens):
        word = tokens[i]
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", word) or word.startswith("-"):
            i += 1
            continue
        name = os.path.basename(word.lstrip("\\"))
        if name in WRAPPERS:
            i += 1
            if name == "timeout" and i < len(tokens) and re.fullmatch(r"[0-9.]+[smhd]?", tokens[i]):
                i += 1
            continue
        if is_rm(word):
            return True
        if name in SHELLS:
            rest = tokens[i + 1:]
            for j, arg in enumerate(rest):
                if arg == "-c" and j + 1 < len(rest):
                    return command_runs_rm(rest[j + 1])
            return False
        if name == "find":
            rest = tokens[i + 1:]
            return any(arg in ("-exec", "-execdir", "-ok", "-okdir") and j + 1 < len(rest) and is_rm(rest[j + 1])
                       for j, arg in enumerate(rest))
        return False
    return False


def command_runs_rm(command):
    text = re.sub(r"\$\(|`|\n", " ; ", command)
    try:
        lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|()")
        lexer.whitespace = " \t\r"
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return re.search(r"(^|[\s;&|(`])\\?(/usr)?(/bin/)?rm(\s|$)", command) is not None
    segment = []
    for token in tokens + [";"]:
        if token in SEPARATORS or "\n" in token:
            if segment and runs_rm(segment):
                return True
            segment = []
        else:
            segment.append(token)
    return False


def main():
    if any(arg in ("--help", "-h") for arg in sys.argv[1:]):
        print("Usage: block-rm.py [--help|-h]\nRead a PreToolUse JSON payload from stdin; deny recognized rm commands.\nOutput language: HSKILLS_LANG=en (default) or zh.")
        return
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command_runs_rm(command):
        return
    reason = (
        "这台机器不用 rm 删除（「マスター」的规定，这个 hook 拦的就是它），命令没有执行。"
        + TRASH_HINT.get(sys.platform, TRASH_HINT["linux"])
        + "或者干脆不删：临时目录换一个 mktemp -d 新建的空目录用。"
        "不要换别的命令（unlink、find -delete、脚本里的删除函数）绕过；真需要永久删除，把精确命令交给「マスター」。"
    )
    if os.environ.get("HSKILLS_LANG", "en") != "zh":
        hint = ("Use trash <path> (/usr/bin/trash) to move items to Trash, where Finder can restore them. "
                if sys.platform == "darwin" else
                "Use gio trash <path> for recoverable deletion. If cross-mount paths such as /tmp are unsupported, "
                "move items into ~/.local/share/Trash/files/ and write matching ~/.local/share/Trash/info/<name>.trashinfo metadata. ")
        reason = ("This machine does not use rm for deletion; the command was not executed. " + hint
                  + "Alternatively, leave the items and use a new empty directory from mktemp -d. "
                  "Do not bypass this hook with unlink, find -delete, or scripted deletion. "
                  "If permanent deletion is necessary, present the exact command to the user.")
    json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                      "permissionDecision": "deny",
                                      "permissionDecisionReason": reason}}, sys.stdout, ensure_ascii=True)


if __name__ == "__main__":
    main()
