---
name: trash
description: 在 Windows 上删除文件或目录时用 trash 命令移进回收站，可还原。任何要删、清理、移走文件或目录的动作，包括用户说"删了""清掉""扔了"的时候，用它代替 rm、del、Remove-Item。
metadata:
  verified:
    by: ai:gemini
    at: 2026-11-14
  sources:
    - resource: "scripts/trash.ps1"
      title: "仓库内置 PowerShell 回收站脚本"
---

# trash

把文件或目录移进 Windows 回收站，不是永久删除。删除类动作一律用它，不用 `rm`、`del`、`Remove-Item`。

## 用法

```powershell
trash <路径> [<路径>...]      # 多参数、通配符、含空格路径都行
trash --dry-run <路径>        # 只预览，不删
trash --help
```

目录整棵进回收站，文件单个进。路径不存在只警告不中断。全部成功 exit 0，任一失败 exit 1。

## 本机事实（2026-09-02 核验）

- 将 `skills/trash/scripts` 加入 `PATH` 后，PowerShell 可直接调 `trash`。cmd 需要建立同名转发 shim（如同目录的 `trash.cmd`，调用 PowerShell 执行内置 `trash.ps1` 并转交参数）；配置好 shim 后，两种 shell 都可直接调 `trash`。
- **Git Bash 里找不到它**（shim 是 .cmd），Claude Code 的 Bash 工具要删东西时改用 PowerShell 工具跑 `trash`。
- git 跟踪的文件用 `git rm`，历史本身就是回收站。

## 顺序

先 `--dry-run` 看一遍要删的清单，再真删。获批的范围之外的路径不加进参数。
