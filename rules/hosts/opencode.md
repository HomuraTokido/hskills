# opencode 差量

通用纪律由 `opencode.json` 的 `instructions` 指向 HSkills 的 `rules/core.md` 加载（这个宿主不解析 `@`），这里只放 opencode 自己的。Shell 输出纪律已收进 core，不在这里重复。本文件按平台分节，`build.py --install --host opencode` 只装公共部分加本平台那一节。

## 目录与加载

- 这个宿主除了 `~/.config/opencode/AGENTS.md` 还会读 `~/.claude/CLAUDE.md` 和 `~/.claude/skills`，环境变量 `OPENCODE_DISABLE_CLAUDE_CODE=1` 关掉，避免同一份纪律和 skill 进两次。
- `~/.config/opencode/skills` 只放 hotlist 上的热 skill，由 skillshare 从 HSkills 复制，不手改。

## 通用：嵌套引号写成文件，不内联

`python -c "…"`、`ssh "…"` 里嵌套双引号、`$( )`、`\n` 时，外层 shell 会先解释转义，导致语法错、变量提前展开、引号失效。正确做法是用 Write 工具把脚本落成文件再执行，IP、密码、API key 放脚本内变量，不内联进命令行。

## Windows

- 宿主 shell 是 PowerShell 7（`pwsh`）。命令按 PowerShell 7 语法写：`Get-Content`、`Set-Content`、`Get-ChildItem`、`& "带空格的路径\exe" 参数`、`python script.py`。不用 `cat << EOF`、`echo > file`、`ls -la`、`grep`、`awk` 这类 bash 写法。
- `$env:VAR` 读环境变量，`$()` 子表达式，路径用双引号；含 `$` 的字符串不用单引号包，会被字面解析。
- 输出含中文时走 Read / Write 工具，不走 PowerShell 管道；代码页已全局设为 65001。

## macOS

- 宿主 shell 是 POSIX shell，按 POSIX 写。具体以本回合实际拿到的 shell 工具为准（见 core 的「环境」）。
- 装在 `/opt/homebrew/bin/opencode`。
