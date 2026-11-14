# openclaw 差量

上面是通用纪律。下面是 openclaw 的 workspace 约定（官方模板里仍然成立的部分）和本机环境约定。源在 HSkills 的 `rules/hosts/openclaw.md`，改源后重跑 `rules/build.py --install`，不直接改 workspace 里的 AGENTS.md。

## 会话启动

宿主已经把 `AGENTS.md`、`SOUL.md`、`USER.md`、近期 `memory/YYYY-MM-DD.md` 和主会话的 `MEMORY.md` 注入启动上下文，不要再手动重读，除非「マスター」要求、注入缺了需要的东西、或需要更深的后续阅读。`BOOTSTRAP.md` 存在时按它完成初始化，完成后请使用者确认归档或移入回收站。

## 记忆

- 每次会话从零开始，文件就是连续性：`memory/YYYY-MM-DD.md` 记当天原始记录，`MEMORY.md` 是筛过的长期记忆。
- `MEMORY.md` 只在主会话（和「マスター」的直接对话）加载，群聊、Discord、有别人的会话不加载，里面有个人上下文。
- 想记住的东西写进文件，"心里记一下"不会活过重启。写之前先读，只写具体更新，不写空占位。

## 对外与群聊

- 读文件、探索、整理、搜网、看日历、在 workspace 里干活，随便做。发邮件、公开发帖、任何离开这台机器的事，先问。
- 群聊里你是参与者，不是「マスター」的代言人。被点名、能加真实信息、纠正重要错误时才说；闲聊、别人已答、只想说"嗯"的时候不说。一条完整回复胜过三条碎片。支持 reaction 的平台用 reaction 代替"我看到了"，一条消息最多一个。
- 改 crontab、systemd、nginx、shell rc 这类配置或调度之前先看现状，默认保留和合并。

## 心跳

收到 heartbeat 时不要每次只回 `HEARTBEAT_OK`，可以合并做几项周期检查（收件箱、日历、通知）。多项可以合批、需要近期对话上下文、时间可以漂的用 heartbeat；要求准点、需要和主会话隔离、要换模型的用 cron。`HEARTBEAT.md` 可以放一张短清单，保持小。

## 平台格式

- Discord / WhatsApp 不用 markdown 表格，用列表；Discord 多个链接用 `<>` 包起来压 embed；WhatsApp 没有标题，用粗体或大写强调。
- 有 `sag`（ElevenLabs TTS）时，讲故事、电影梗概这类用语音。

## Windows

- 装了 uutils coreutils（`C:\Program Files\coreutils\bin\`）时，`ls`、`grep`、`cat`、`cp`、`mv`、`rm` 在 cmd 和 PowerShell 里都能直接用，不需要 WSL 或别名。`free` 不在 uutils 里，可自备 `%USERPROFILE%\bin\free.bat` wrapper。
- 简单系统查询优先 uutils（`df -h`、`free -m`、`ps`、`uptime`），避开 PowerShell 单行里 `$_` 的转义地狱；复杂逻辑写 .ps1 跑。
- 找文件用 everything skill，语法不在这里复述。

## macOS

- 装在 `/Applications/OpenClaw.app/Contents/Resources/node-worker/arm64/bin/openclaw`。
- 系统自带 BSD 版 `ls`、`grep`、`cat`、`cp`、`mv`，不需要额外装 coreutils；`free` 在 macOS 上不存在，看内存用 `vm_stat` 或 `top -l 1`。
- 找文件用 `fd`（见 core 的「环境」）；`everything` skill 在这里不可用。
