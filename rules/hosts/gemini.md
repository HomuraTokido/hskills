@__HSKILLS_ROOT__/rules/core.md
@[core](__HSKILLS_ROOT__/rules/core.md)

# Antigravity / Gemini 差量

通用纪律在 HSkills 的 `rules/core.md`，由文件顶部的引用行展开；这里只放 Antigravity / Gemini 宿主自己的。本文件按平台分节，`build.py --install --host gemini` 只装公共部分加本平台那一节。

## 检索与读取边界

- 查文件只搜直接相关的、和可能有关的，不搜只有一丝半点可能性有关的；必要且足够就停。只读一样烧 token，不靠遍历周边文件找安全感。

## 规则加载与内联语法

- **两套宿主的内联语法互不兼容**：Antigravity（IDE / Desktop 2.0 / `agy` CLI）只展开 `@[label](path)` 宏（展开后单文件上限 24,000 bytes，全局与 `always_on` 规则共享 20,000 tokens 预算）；Gemini CLI（`gemini`）只展开裸 `@path`。本平台那一节并列写两行，两边各自展开一次 `core.md`，不认识的那一行留作单行字面文本。若本回合 `<user_rules>` 里没有看到 `core.md` 正文被展开，第一轮先读一次那两行指向的 `core.md`。
- **层级发现**：Antigravity 原生按层级加载全局（`~/.gemini/GEMINI.md`、`~/.gemini/AGENTS.md`、`~/.gemini/config/`）及项目各级目录的 `AGENTS.md`、`GEMINI.md`、`.agents/rules/*.md`（注：`.agents/rules/*.md` 必须带合法的 YAML frontmatter `trigger`，否则会被静默丢弃）。旧 Gemini CLI 默认只认 `GEMINI.md`，需在 `~/.gemini/settings.json` 设 `context.fileName: ["AGENTS.md", "GEMINI.md"]`。
- **Skill 发现**：从 `~/.agents/skills` 和 `~/.gemini/skills` 读取，`~/.agents` 优先；同名会各列一份。

## MCP 与派工路由

- **MCP 挂载位置**：Antigravity 全局 MCP 配置在 `~/.gemini/config/mcp_config.json`（及 `~/.gemini/antigravity/mcp_config.json`）。工具默认按 Lazy 模式暴露，每个服务在 `~/.gemini/antigravity/mcp/<serverName>/` 下有 `<toolName>.json` 参数 schema 和握手下发的 `instructions.md`，通过 `call_mcp_tool` 调用。
- **Hwiki**：查和写走 `hwiki` MCP（`document_search`、`archive_search`、`archive_show`、`ai_note_write`）；本机路径见本平台那一节。
- **派工（specialist-subagents）**：日常派工走 `specialist-subagents` MCP。Antigravity 不会把 MCP 握手时的 `instructions` 自动拼进 system prompt，首次派工前先读一次 `~/.gemini/antigravity/mcp/specialist-subagents/instructions.md`（或调 `dispatch_guide`）。Antigravity 没有接座位完成的自动会话唤醒，`seat_start` 后用 `run_command` 跑返回结果 `next` 里的 `wait` 命令或调 `task_wait`，不轮询 `seat_show` / `seat_list`。

## Windows

- Hwiki（若已接入）默认示例路径在 `~/hwiki`（按本机克隆目录修改）。
- `~/.gemini/skills` 现在不由 skillshare 管，热 skill 要用就先在 skillshare 加回 gemini target。

## macOS

- Hwiki 在 `~/hwiki`；specialist-subagents 服务在 `~/specialist-subagents`。
- `run_command` 跑的是 zsh（按 POSIX 写），但其沙箱对 `~/.gemini` 等目录会报 `Operation not permitted`；读写这类宿主配置文件直接用内置的 `view_file`、`write_to_file`、`replace_file_content`。
- 删文件用系统自带的 `/usr/bin/trash`。

## Linux

- Hwiki 在 `~/hwiki`；specialist-subagents 服务在 `~/specialist-subagents`。
- 删除只用本机配置的可恢复回收站命令（如 `gio trash` 或 `trash-put`），不用 `rm`。
