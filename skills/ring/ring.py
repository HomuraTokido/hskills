"""ring.py - 在电脑上模拟一通打进来的电话，用来通知「マスター」一件事做完了。

用法:
    python ring.py "任务做完了，要来看一眼吗"
    python ring.py --from "Claude" --timeout 30 "卡住了，需要你决定"

行为:
    弹一个来电样式的窗口，文字直接显示在窗口里，同时响铃。
    我知道了 -> 关掉，打印「マスター」已经知道了。只有点击按钮才算确认；其他关闭均不算确认。
    超时     -> 打印 响了 N 秒，未点击确认按钮，不要再打。
    结果直接打印成一句话给调用方读，同时追加一行到 ~/.ring/calls.log。
    加 --speak 会同时用系统语音念出这句话，默认不念。

只用标准库，铃声和语音都用 Windows 自带的。
"""

import argparse
import base64
import ctypes
from ctypes import wintypes
import datetime
import os
import subprocess
import threading
import winsound

LOG = os.path.join(os.path.expanduser("~"), ".ring", "calls.log")
DEFAULT_SOUND = os.path.join(os.environ.get("SystemRoot", "C:/Windows"), "Media", "Ring01.wav")


def require_visible_desktop():
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.GetThreadDesktop.argtypes = [wintypes.DWORD]
    user32.GetThreadDesktop.restype = wintypes.HANDLE
    user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    user32.OpenInputDesktop.restype = wintypes.HANDLE
    user32.GetUserObjectInformationW.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
        wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
    ]
    user32.GetUserObjectInformationW.restype = wintypes.BOOL
    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
    user32.CloseDesktop.restype = wintypes.BOOL
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD

    def name(handle):
        buffer = ctypes.create_unicode_buffer(256)
        needed = wintypes.DWORD()
        if not user32.GetUserObjectInformationW(
            handle, 2, buffer, ctypes.sizeof(buffer), ctypes.byref(needed)
        ):
            raise ctypes.WinError()
        return buffer.value

    current = user32.GetThreadDesktop(kernel32.GetCurrentThreadId())
    if not current:
        raise ctypes.WinError()
    active = user32.OpenInputDesktop(0, False, 0x0001)
    if not active:
        raise RuntimeError('无法访问用户当前桌面；未响铃。')
    try:
        current_name, active_name = name(current), name(active)
    finally:
        user32.CloseDesktop(active)
    if current_name.casefold() != active_name.casefold():
        raise RuntimeError(
            f'来电窗口不可见：当前桌面 {current_name}，用户桌面 {active_name}；'
            '请在真实 Windows 用户层运行。未响铃。'
        )


def ring_start(path):
    # Windows 自带 Ring01 到 Ring10 十个电话铃声，循环播放直到停止。
    winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)


def ring_stop():
    winsound.PlaySound(None, winsound.SND_PURGE)


def show_window(caller, text, timeout):
    script = r'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = '来电'
$form.ClientSize = New-Object System.Drawing.Size(360, 260)
$form.StartPosition = 'Manual'
$area = [System.Windows.Forms.Screen]::FromPoint([System.Windows.Forms.Cursor]::Position).WorkingArea
$form.Location = New-Object System.Drawing.Point(
    ($area.Left + [int](($area.Width - $form.Width) / 2)),
    ($area.Top + [int](($area.Height - $form.Height) / 2)))
$form.Add_Shown({ $form.Activate() })
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.TopMost = $true
$form.BackColor = [System.Drawing.Color]::FromArgb(30, 30, 30)

$kind = New-Object System.Windows.Forms.Label
$kind.Text = '来电'
$kind.ForeColor = [System.Drawing.Color]::FromArgb(154, 154, 154)
$kind.Font = New-Object System.Drawing.Font('Microsoft YaHei', 11)
$kind.TextAlign = 'MiddleCenter'
$kind.SetBounds(20, 20, 320, 28)
$form.Controls.Add($kind)

$caller = New-Object System.Windows.Forms.Label
$caller.Text = $env:RING_CALLER
$caller.ForeColor = [System.Drawing.Color]::White
$caller.Font = New-Object System.Drawing.Font('Microsoft YaHei', 22, [System.Drawing.FontStyle]::Bold)
$caller.TextAlign = 'MiddleCenter'
$caller.SetBounds(20, 50, 320, 48)
$form.Controls.Add($caller)

$message = New-Object System.Windows.Forms.Label
$message.Text = $env:RING_TEXT
$message.ForeColor = [System.Drawing.Color]::FromArgb(221, 221, 221)
$message.Font = New-Object System.Drawing.Font('Microsoft YaHei', 11)
$message.TextAlign = 'MiddleLeft'
$message.SetBounds(20, 105, 320, 70)
$form.Controls.Add($message)

$button = New-Object System.Windows.Forms.Button
$button.Text = '我知道了'
$button.Font = New-Object System.Drawing.Font('Microsoft YaHei', 11)
$button.BackColor = [System.Drawing.Color]::FromArgb(39, 174, 96)
$button.ForeColor = [System.Drawing.Color]::White
$button.FlatStyle = 'Flat'
$button.SetBounds(105, 198, 150, 36)
$form.Controls.Add($button)

$script:outcome = 'dismissed'
$button.Add_Click({ $script:outcome = 'ack'; $form.Close() })

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = [Math]::Max(1, [int]$env:RING_TIMEOUT) * 1000
$timer.Add_Tick({ $timer.Stop(); $script:outcome = 'timeout'; $form.Close() })
$timer.Start()
[void]$form.ShowDialog()
$timer.Dispose()
$form.Dispose()
Write-Output $script:outcome
'''
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    env = os.environ.copy()
    env["RING_CALLER"] = caller
    env["RING_TEXT"] = text
    env["RING_TIMEOUT"] = str(timeout)
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown WinForms error"
        raise RuntimeError(f"ring window failed: {detail}")
    result = completed.stdout.strip().splitlines()[-1:]
    if not result or result[0] not in {"ack", "timeout", "dismissed"}:
        raise RuntimeError("ring window returned no valid outcome; confirmation unknown")
    return result[0]


def speak(text):
    # 通过 PowerShell 调 SAPI，避免第三方依赖。
    safe = text.replace("'", "''")
    cmd = f"$v = New-Object -ComObject SAPI.SpVoice; $v.Speak('{safe}') | Out-Null"
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def log(outcome, caller, text):
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{stamp}\t{outcome}\t{caller}\t{text}\n")
    except OSError:
        pass  # 沙箱里写不了就算了，打印出来的那句话才是结果。


def main():
    p = argparse.ArgumentParser(description="模拟一通来电")
    p.add_argument("text", help="要告诉「マスター」的一句话")
    p.add_argument("--from", dest="caller", default="Agent", help="来电人名字")
    p.add_argument("--timeout", type=int, default=30, help="响铃多少秒算没人管")
    p.add_argument("--sound", default=DEFAULT_SOUND, help="铃声 wav 文件，默认 Windows 自带 Ring01.wav")
    p.add_argument("--speak", action="store_true", help="同时用系统语音念出这句话")
    a = p.parse_args()
    if not 1 <= a.timeout <= 86400:
        p.error("--timeout must be between 1 and 86400 seconds")

    ACKNOWLEDGED = "「マスター」已经知道了。"
    TIMEOUT = f"响了 {a.timeout} 秒，未点击确认按钮，不要再打。"
    DISMISSED = "来电窗口已关闭，未点击确认按钮。"

    require_visible_desktop()
    if a.speak:
        threading.Thread(target=speak, args=(a.text,), daemon=True).start()
    try:
        ring_start(a.sound)
        status = show_window(a.caller, a.text, a.timeout)
        outcome = {"ack": ACKNOWLEDGED, "timeout": TIMEOUT, "dismissed": DISMISSED}[status]
    finally:
        ring_stop()

    print(outcome)
    log(outcome, a.caller, a.text)


if __name__ == "__main__":
    main()
