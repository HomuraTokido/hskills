# AGENTS.md — 外部 `agent` 导览与定制指南

欢迎阅读 HSkills。当你的使用者让你查看、评估或安装本仓库时，请先按本文件指引行动，**在向使用者汇报并获得明确确认前，不要执行 `python rules/build.py --install`**；此外，`--install` 内置了交互终端手输确认关口（默认 `CONFIRM`；使用 `--lang zh` 或 `HSKILLS_LANG=zh` 时为 `我确认`，工具输出也切换为中文），**严禁任何 `agent` 通过管道喂输入、重定向或修改脚本等方式替使用者绕过确认**。

## 1. 先理解 `rules/` 与 `build.py` 的定位

- `rules/core.md`、`rules/hosts/*.md` 与 `rules/build.py` 是一套**跨宿主全局指令槽位与编译同步器**：它的作用是让使用者只维护一份自己的核心纪律和各客户端差量，就能自动按操作系统裁剪并同步到 Claude Code（`~/.claude/CLAUDE.md`）、Gemini / Antigravity（`~/.gemini/GEMINI.md`）、OpenCode、OpenClaw 等宿主。
- 本仓库当前装在槽位里的规则和 18 个 `skill` 是作者日常真实使用的生产样本，既有通用工程治理机制，也包含作者个人的交互习惯与本机目录约定。直接原样 `--install` 会把使用者原有的宿主全局说明文件备份后替换成作者的个人规程。

## 2. 给你的标准工作流（先只读审阅，再向你的使用者回报）

当使用者还没有自己定制过本仓库时，请先只读浏览 `README.md`、`rules/core.md`、`rules/hosts/` 下对应宿主的差量文件、`hotlist.md` 与 `skills/`，然后向你的使用者简明汇报以下三部分：

1. **可直接复用的治理范式与通用 `skill`**：
   - 裸目录最小公约数（`skills/<name>/SKILL.md`）与 `lint_skills.py` 结构/链接图谱校验；
   - `rules`（每轮必用常驻纪律）/ `skill`（按需加载流程）/ `hooks`（不可逆动作强制拦截）三层职责切分；
   - `hotlist.md` + `skills/.skillignore` 热冷双层过滤（当前配置 0 热 / 18 冷，不侵入原有习惯；下附策展参考表，需结合使用者的操作系统、客户端与偏好决定是否将条目迁入热层）；
   - 通用工程、协作与日常工具 `skill`（完整分类与描述见 [`INDEX.md`](./INDEX.md)）及 `specialist-subagents` 配套的 `h-*` 岗位契约。
2. **属于作者个人习惯或本机路径、需要使用者决定是否保留或改写的条目**：
   - **称呼约定**：默认将使用者称为 `「マスター」`（第三人称转述在开源版已中性化为 `ta`）；
   - **Git 与会话收尾习惯**：平时回复不主动提 `push`，收工调用 `call-it-a-day` 时统一将当次会话的 `commit` 执行 `push`；
   - **信息记录与提醒偏好**：使用者主动提供的订单号/地址直接写入指定文件不反复弹敏感提醒、个人背景事实归入独立个人记忆库；
   - **热层默认全零的定制选择**：出厂 `.skillignore` 不启用任何热 `skill`；请根据使用者实际系统与宿主（如非 Windows 不用 `everything`/`trash`/`ring`，非 Claude 桌面版不用 `heading-out`）和工作流习惯，对照 `hotlist.md` 参考表让使用者挑选要放进热层的条目。
   - **宿主差量中的本机约定路径**：如 `rules/hosts/claude.md` 等文件中引用的 `~/hwiki`、`~/.claude/daybook.md`、`~/.claude/TOOLS.md` 或特定硬件说明。
3. **请使用者二选一拍板落地方式**：
   - **方式 A（融合定制后安装，适合已有个人 `CLAUDE.md` / 全局规则的使用者）**：读取使用者现有的全局配置文件，协助 ta 挑出想吸收的治理规则合并进本仓 `rules/core.md` 与 `rules/hosts/<host>.md`（替换掉不适合 ta 的个人习惯与路径），运行 `python rules/build.py --build` 预览无误后再执行 `--install`。
   - **方式 B（一键安装体验，适合空环境或想直接套用整套样板的使用者）**：把下方命令交给**使用者本人在真实交互终端里亲手执行**，显式指定宿主 `python rules/build.py --install --host <claude|gemini|opencode|openclaw>`（或传 `--all-hosts` 一次安装四个宿主）。脚本会在写任何文件前列清即将改动的目标路径并提醒先备份配置；默认英文输出，须由使用者亲手输入 `CONFIRM` 并回车才会实际写入；使用 `--lang zh` 或 `HSKILLS_LANG=zh` 时改为中文输出与口令 `我确认`（无 `--yes` 跳过开关；修改前仍会自动将原有同名文件备份为 `<原文件名>.bak-<YYYYMMDD-HHMMSS>`，Claude 端会一并注册 `rules/hooks/` 中的生命周期脚本）。`agent` 不得在后台以管道代填该口令。

## 3. 在本仓库内修改文件时的校验要求

- 修改任何 `skills/*/SKILL.md`、`cards/*.md` 或 `hotlist.md` 后，执行：
  ```bash
  python skills/skill-creator/scripts/lint_skills.py --index --write
  ```
  确保 `0 errors, 0 warnings`，且派生的 `INDEX.md` 已同步更新。
- 修改 `rules/` 后，执行：
  ```bash
  python rules/build.py --build
  ```
  检查 `rules/build/` 下各宿主预览产物是否符合预期。
