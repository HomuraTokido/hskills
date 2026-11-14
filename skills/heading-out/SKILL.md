---
name: heading-out
description: 「マスター」要出门、之后用手机接着看或接着干时，确保ta要的会话在手机上连得上：给这些会话打开 Remote Control，报告每个会话的连接状态，说清这台电脑在ta不在时会不会断。ta说「我出门了」「我要出门了」「出门一趟」「去公司了」「去上班了」「路上用手机看」「我用手机接着弄」这类话时用，哪怕没提到 Remote Control 或手机。只在 Claude 桌面版里用（有 set_remote_control 工具的宿主）；别的宿主没有这条路，告诉ta一句就行。同时是收工的（「干到这里了我要出门了」），先做这个，再按 call-it-a-day 清点。
metadata:
---

# heading-out

ta要离开电脑，但还要用手机（Claude app 的 Code，或 claude.ai/code）接着看、接着干。这个 skill 只管一件事：ta走之前，要用的会话都连上了，连不上的ta当场知道。

## 为什么要专门做

桌面版只在会话里发出一条消息的时候，才给那个会话接上 Remote Control。桌面版重启、电脑开机之后，所有会话都是断的，要等有人在桌面上往里面发消息才会接上。ta在外面打开手机时发现连不上，已经来不及了。

历史观察（2026-10-29；具体行为以当前版本为准）：main.log 里 `[rcAutoEnable]` 的触发只有 first_turn、warm_send、cold_resume 三种，没有「启动时恢复」。设置「Connect new sessions to Remote Control」开着时，新会话第一轮会自动接上。按文件夹开新会话的那条路（`~/.config/Claude/logs/remote-control.log`，在手机上新开会话用）开机后就在，和已有会话断不断无关。

## 做什么

1. **定哪些会话要接。** 这个会话本身（`set_remote_control` 的 `session_id` 填 `"self"`）一定接。ta点了名的接上；正在跑的（`list_sessions` 里 `isRunning` 为 true）也接上，因为它们跑完会等ta。其余的不猜，报告里列最近活动的几个，告诉ta要接哪个说一声。
2. **打开。** 工具是 `mcp__ccd_session_mgmt__set_remote_control`，工具是延迟加载的就先用 ToolSearch 载入。已经连着的（`list_sessions` 的 `remoteControlActive` 为 true，或者这一轮已经开过）再开一次也不会变。别的会话不在活动状态时直接开会被拒（「Remote Control requires an active session. Send a message first.」）：先用 `mcp__ccd_session_mgmt__send_message` 给它发一句「测试 Remote Control，不用做任何事，只回一句收到」，再开。不要叫ta去电脑上点按钮，ta已经要走了。返回 `connecting` 的，过几秒用 `list_sessions` 再看一次；`unavailable` 或被拒（从别的设备开的会话），写进报告。

   本机实测（2026-10-29）：auto 模式下开自己和别的会话都没弹批准卡；对断开的会话先发消息再开，返回 `on`，`remoteControlActive` 变成 true。别的权限模式下会弹卡，要ta在离开前点。
3. **看这台电脑会不会断。** 电脑会不会睡、桌面版有没有可能被关掉，按宿主工具文件的现状说（以本机 TOOLS.md 或系统设置为准）。会睡的，告诉ta，不替ta改电源设置。

## 怎么报

ta要走了，在手机上看。第一句给结论：能走，还是有几个会话没连上。然后每个会话一行：标题加状态（已连上 / 连接中 / 连不上和原因）。最后一行：出门前在手机上打开 Code，点进那个会话看一眼，点得进去就算连上。

## 坑

- 桌面版重启、电脑重启之后，这次开的都会断，要重新做一遍。这是目前唯一确认过的断法。
- 会话空闲 30 分钟后桌面版会把它转进后台，这会不会断开 Remote Control，未验。
- ta已经在手机上了、在会话里让我再接别的会话：工具能不能从手机驱动的会话里调用、批准卡弹在哪，未验。

## Skill links

- related: [call-it-a-day](../call-it-a-day/SKILL.md) — 出门同时是收工时，接好会话之后转去清点尾巴
