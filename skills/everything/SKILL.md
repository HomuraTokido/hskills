---
name: everything
description: 用 Everything 的命令行 es.exe 在本机 Windows 上秒级搜文件、按目录/扩展名/时间/大小过滤、数副本。需要全盘找文件、列某目录下的东西、做 inventory，或 es.exe 报 Error 8 时使用。
metadata:
  verified:
    by: ai:gemini
    at: 2026-11-14
  sources:
    - resource: https://www.voidtools.com/support/everything/command_line_interface/
      title: Everything CLI (es.exe) 官方参数与搜索语法参考
---

# everything

es.exe 是 Everything 的命令行接口。它不建索引，只通过 IPC 向正在运行的 Everything 主程序要结果。

## 本机事实（2026-09-02 核验）

- 主程序 `C:\Program Files\Everything\Everything.exe`，1.5.0.1415b。
- CLI `%LOCALAPPDATA%\Programs\EverythingCLI\es.exe`，1.1.0.37，已在 PATH。ES 没有 1.5 版，1.1 直接对 1.5 默认实例可用，不要加 `-instance`。
- 旧版 1.1.0.30 备份为同目录的 `es.exe.bak`。

## Error 8（IPC window not found）

主程序没在跑，或只有服务进程在跑。服务进程没有 IPC 窗口，进程列表里有 Everything 不等于能搜。处方：

```powershell
Start-Process 'C:\Program Files\Everything\Everything.exe'; Start-Sleep 3
```

然后重试。仍失败再考虑沙盒隔离了窗口消息，提权重跑。提权不是必须，沙盒内正常时直接用。

## 坑（实测）

- 空格是 AND，但每个词默认只匹配**文件名**。目录名要写 `path:`。`es.exe skill-creator SKILL.md` 返回 0，要写 `es.exe path:skill-creator wfn:SKILL.md`。
- **Git Bash 里不要用 `/ad` `/a-d`**，MSYS 会把它们当路径转换掉，静默返回空。用 Everything 自己的 `folder:` `file:`，或前缀 `MSYS_NO_PATHCONV=1`。
- Claude Code 的 Bash 工具（Windows）会把命令里的 `\` 折成 `\`，单引号里也一样。单个反斜杠照写即可（`path:HSkills\skills` 没问题）；正则里要一个字面反斜杠就写四个。
- PowerShell 里分号是命令分隔符，`ext:zip;rar` 要整体加引号。
- 结果永远是真实路径。junction / symlink 挂进 agent 的目录只出现在目标位置。
- `-r` 正则默认只匹配文件名，要匹配整个路径加 `-p`。
- `parent:` 在 ES 1.1 返回空。要"某目录的直接子项"用 `-p -r` 限深度：`es.exe -p -r 'HSkills\\skills\\[^\\]+$'`。

## 常用形态

```bash
es.exe 关键词 -n 20                                   # 永远加 -n
es.exe path:name wfn:SKILL.md                         # 某目录下的某文件，wfn = 整个文件名
es.exe ext:py path:Documents                          # 限定目录
es.exe 关键词 -size -dm -sort date-modified-descending -n 20
es.exe 关键词 -get-result-count                       # 只要数量
es.exe folder: 关键词                                 # 只要文件夹（Git Bash 下代替 /ad）
```

## 完整参考

- CLI 选项：`es.exe -h`，291 行，随装随有。
- 搜索语法：Everything 主程序「帮助 > 搜索语法」；线上 voidtools.com/support/everything/searching/。
