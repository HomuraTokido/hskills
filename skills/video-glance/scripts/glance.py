"""video-glance: 让模型低成本"看"一个在线视频——字幕给文字轨，少量关键帧给画面轨。

子命令（不带参数运行等同 --help）：
  meta   URL                      打印标题、作者、时长、简介、分 P、章节；B 站另列字幕清单
  fetch  URL OUTDIR               下载 <=720p 纯视频流（不要音轨）；YouTube 顺带下字幕
  subs   SRC OUT.txt              把 B 站字幕 JSON / .srt / .vtt 转成「[mm:ss] 文本」逐行纯文本
  frames VIDEO OUTDIR ...         按时间点 / 固定间隔 / 场景切换抽帧，可裁区域，拼成总览图

依赖：pip install yt-dlp imageio-ffmpeg（ffmpeg 用 imageio_ffmpeg 自带的 exe，不要求系统装 ffmpeg）。
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"


def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        exe = shutil.which("ffmpeg")
        if exe:
            return exe
        sys.exit("找不到 ffmpeg。先跑：python -m pip install imageio-ffmpeg")


def run(cmd, **kw):
    # stdin 给 DEVNULL：Windows 上子进程继承 MCP/agent 的 stdin 会卡住
    return subprocess.run(cmd, stdin=subprocess.DEVNULL, **kw)


def fmt_t(sec):
    sec = int(sec)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def parse_t(s):
    sec = 0.0
    for part in s.split(":"):
        sec = sec * 60 + float(part)
    return sec


def bvid_of(url):
    m = re.search(r"(BV[0-9A-Za-z]{10})", url)
    return m.group(1) if m else None


def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.bilibili.com/"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


# ---------- meta ----------

def cmd_meta(a):
    bv = bvid_of(a.url)
    if bv:
        d = http_json(f"https://api.bilibili.com/x/web-interface/view?bvid={bv}")
        if d.get("code") != 0:
            sys.exit(f"B 站接口返回 code={d.get('code')} message={d.get('message')}")
        d = d["data"]
        print(f"标题: {d['title']}\n作者: {d['owner']['name']}\n时长: {fmt_t(d['duration'])}\nbvid: {bv}")
        for p in d["pages"]:
            print(f"P{p['page']}: cid={p['cid']} {fmt_t(p['duration'])} {p['part']}")
        print("简介:\n" + d["desc"])
        subs = (d.get("subtitle") or {}).get("list") or []
        if subs:
            print("字幕清单（不登录时拿不到下载地址；取法见 SKILL.md「B 站字幕」）:")
            for s in subs:
                print(f"  lan={s['lan']} {s['lan_doc']}")
        else:
            print("字幕清单: 不登录时为空。登录后常有 ai-zh（B 站 AI 字幕），取法见 SKILL.md。")
        return
    r = run([sys.executable, "-m", "yt_dlp", "-J", "--no-warnings", a.url], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(r.stderr[-2000:])
    d = json.loads(r.stdout)
    print(f"标题: {d.get('title')}\n作者: {d.get('uploader')}\n时长: {fmt_t(d.get('duration') or 0)}")
    for c in d.get("chapters") or []:
        print(f"章节 {fmt_t(c['start_time'])} {c['title']}")
    print("简介:\n" + (d.get("description") or ""))
    print("人工字幕: " + ", ".join(sorted((d.get("subtitles") or {}).keys())))
    auto = sorted((d.get("automatic_captions") or {}).keys())
    print("自动字幕: " + (", ".join(a for a in auto if a.startswith(("zh", "en", "ja"))) or "无"))


# ---------- fetch ----------

def cmd_fetch(a):
    os.makedirs(a.outdir, exist_ok=True)
    cmd = [sys.executable, "-m", "yt_dlp", "--no-warnings", "--ffmpeg-location", ffmpeg_exe(),
           "-f", f"bv*[height<={a.height}][vcodec^=avc]/bv*[height<={a.height}]/b[height<={a.height}]",
           "--throttled-rate", "50K", "-o", os.path.join(a.outdir, "video.%(ext)s")]
    if not bvid_of(a.url):
        cmd += ["--write-subs", "--write-auto-subs", "--sub-langs", a.sub_langs, "--sub-format", "vtt/srt/best"]
    if a.cookies:
        cmd += ["--cookies", a.cookies]
    r = run(cmd + [a.url])
    if r.returncode:
        sys.exit(f"yt-dlp 退出码 {r.returncode}")
    for f in sorted(os.listdir(a.outdir)):
        print(os.path.join(a.outdir, f))


# ---------- subs ----------

def cmd_subs(a):
    src = a.src
    if src.startswith(("http://", "https://", "//")):
        url = "https:" + src if src.startswith("//") else src
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode("utf-8")
        ext = ".json"
    else:
        text = open(src, encoding="utf-8-sig").read()
        ext = os.path.splitext(src)[1].lower()
    lines = []
    if ext == ".json" or text.lstrip().startswith("{"):
        for x in json.loads(text)["body"]:
            lines.append((x["from"], x["content"]))
    else:  # srt / vtt
        cur = None
        for ln in text.splitlines():
            m = re.match(r"(\d+:)?(\d+):(\d+)[.,](\d+)\s+-->", ln.strip())
            if m:
                cur = parse_t(ln.split("-->")[0].strip().replace(",", "."))
                continue
            ln = re.sub(r"<[^>]+>", "", ln).strip()
            if cur is not None and ln and not ln.isdigit():
                if not lines or lines[-1][1] != ln:  # YouTube 自动字幕逐行滚动，去掉重复
                    lines.append((cur, ln))
    with open(a.out, "w", encoding="utf-8") as f:
        for t, s in lines:
            f.write(f"[{fmt_t(t)}] {s}\n")
    size = os.path.getsize(a.out)
    print(f"{len(lines)} 条，{size // 1024}KB -> {a.out}")


# ---------- frames ----------

def video_duration(ff, video):
    r = run([ff, "-i", video], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0


def scene_times(ff, video, thr):
    r = run([ff, "-hide_banner", "-i", video, "-an",
             "-vf", f"fps=2,scale=320:-2,select='gt(scene,{thr})',showinfo", "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [float(x) for x in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def thin(times, n):
    if len(times) <= n:
        return times
    step = (len(times) - 1) / (n - 1)
    return [times[round(i * step)] for i in range(n)]


def cmd_frames(a):
    ff = ffmpeg_exe()
    dur = video_duration(ff, a.video)
    if a.at:
        times = [parse_t(t) for t in a.at.split(",") if t.strip()]
    elif a.every:
        times = [t for t in range(0, int(dur), a.every)]
    else:
        times = sorted(set([1.0] + scene_times(ff, a.video, a.scene) + [max(dur - 1, 0)]))
        found = len(times)
        times = thin(times, a.max)
        if found > a.max:
            print(f"场景切换找到 {found} 处，均匀抽成 {a.max} 帧（--max 调整）")
    times = [t + a.offset for t in times]
    os.makedirs(a.outdir, exist_ok=True)
    # 先缩到 960 宽，--crop 的坐标都按这个尺寸量
    chain = "scale=960:-2"
    if a.crop:
        # vstack 要求等宽：每块右侧补黑边到最宽那块的宽度
        maxw = max(int(c.split(":")[0]) for c in a.crop)
        parts = [f"crop={c},pad={maxw}:ih:0:0" for c in a.crop]
        if len(parts) == 1:
            chain += "," + parts[0]
        else:
            labels = "".join(f"[s{i}]" for i in range(len(parts)))
            chain += f",split={len(parts)}{labels};" + ";".join(
                f"[s{i}]{p}[c{i}]" for i, p in enumerate(parts))
            chain += ";" + "".join(f"[c{i}]" for i in range(len(parts))) + f"vstack=inputs={len(parts)}"
    index = []
    for i, t in enumerate(times, 1):
        out = os.path.join(a.outdir, f"f_{i:04d}.jpg")
        r = run([ff, "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", a.video, "-frames:v", "1",
                 "-q:v", "3", "-filter_complex", chain, out], capture_output=True, text=True, errors="replace")
        if os.path.exists(out):
            index.append((i, t, out))
        else:
            print(f"第 {i} 帧（{fmt_t(t)}）没截出来，ffmpeg 说：{r.stderr.strip().splitlines()[0] if r.stderr.strip() else '无输出'}")
    if not index:
        sys.exit("一帧都没截出来，见上面 ffmpeg 的报错；多半是 --crop 超出了 960 宽画面的范围。")
    with open(os.path.join(a.outdir, "index.tsv"), "w", encoding="utf-8") as f:
        for i, t, out in index:
            f.write(f"{i}\t{fmt_t(t)}\t{os.path.basename(out)}\n")
    print(f"{len(index)} 帧 -> {a.outdir}（index.tsv 是 序号/时间/文件）")
    if a.tile:
        cols, rows = a.tile.lower().split("x")
        run([ff, "-v", "error", "-y", "-framerate", "1", "-i", os.path.join(a.outdir, "f_%04d.jpg"),
             "-vf", f"tile={cols}x{rows}:padding=4", "-q:v", "3", os.path.join(a.outdir, "sheet_%02d.jpg")])
        sheets = sorted(f for f in os.listdir(a.outdir) if f.startswith("sheet_"))
        per = int(cols) * int(rows)
        for k, s in enumerate(sheets):
            first, last = k * per + 1, min((k + 1) * per, len(index))
            print(f"{os.path.join(a.outdir, s)}  帧 {first}-{last}，按行从左到右")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd")

    m = sp.add_parser("meta", help="元数据、章节、字幕清单")
    m.add_argument("url")

    f = sp.add_parser("fetch", help="下载低清纯视频流（抽帧用）")
    f.add_argument("url")
    f.add_argument("outdir")
    f.add_argument("--height", type=int, default=720)
    f.add_argument("--sub-langs", default="zh.*,en.*,ja.*", help="YouTube 字幕语言（默认 zh.*,en.*,ja.*）")
    f.add_argument("--cookies", help="Netscape 格式 cookies.txt（可选）")

    s = sp.add_parser("subs", help="字幕 JSON/srt/vtt 或其 URL -> 带时间戳纯文本")
    s.add_argument("src", help="本地文件，或 B 站字幕 JSON 的 URL（含 auth_key 的那个）")
    s.add_argument("out")

    fr = sp.add_parser("frames", help="抽帧、裁区域、拼总览图")
    fr.add_argument("video")
    fr.add_argument("outdir")
    g = fr.add_mutually_exclusive_group()
    g.add_argument("--at", help="逗号分隔的时间点，如 1:55,3:12,1:02:08")
    g.add_argument("--every", type=int, help="每 N 秒一帧")
    fr.add_argument("--scene", type=float, default=0.3, help="场景切换阈值（不给 --at/--every 时用，默认 0.3）")
    fr.add_argument("--max", type=int, default=40, help="场景模式的帧数上限（默认 40）")
    fr.add_argument("--offset", type=float, default=0, help="所有时间点统一后移的秒数（章节点常落在转场上，+3~4 秒落到卡片上）")
    fr.add_argument("--crop", action="append", help="w:h:x:y，按 960 宽画面量；可给多次，多块竖直拼在一起")
    fr.add_argument("--tile", help="拼总览图，如 2x11 或 4x4")

    if len(sys.argv) == 1:
        p.print_help()
        return
    a = p.parse_args()
    {"meta": cmd_meta, "fetch": cmd_fetch, "subs": cmd_subs, "frames": cmd_frames}[a.cmd](a)


if __name__ == "__main__":
    main()
