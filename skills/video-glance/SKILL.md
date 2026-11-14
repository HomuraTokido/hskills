---
name: video-glance
description: 用户贴来一个视频链接（bilibili.com/video/BV…、b23.tv、youtube.com、youtu.be 或其他 yt-dlp 支持的站点），要你总结、提炼要点、看看讲了什么、找出视频里提到或画面上写着的东西（价格、型号、代码、表格）时，先读这份再动手，哪怕对方只说「这是一个视频，你看看」「帮我总结一下」。做法是字幕给文字轨、少量关键帧给画面轨，不逐秒截帧；含 B 站登录字幕的取法和抽帧、裁区域、拼总览图的脚本。
metadata:
  verified:
    by: ai:claude-opus-5-5
    at: 2026-10-31
  sources:
    - resource: 2026-10-31 Windows 台式机实测，BV1tCxk6PE9R（68 分钟笔记本选购指南）
      title: B 站字幕、抽帧、裁区域拼图全流程跑通
    - resource: https://github.com/vusallyv/video-context-plugin
      title: 社区通行管线：yt-dlp → 字幕 / Whisper → ffmpeg 场景帧 → 多模态总结
    - resource: https://pypi.org/project/koesub/
      title: B 站 / YouTube 字幕抓取，Whisper 兜底
---

# video-glance

社区做法都是同一条管线：先拿字幕，没有字幕再转写，再抽少量关键帧补画面，最后由模型合起来读。本 skill 把这条管线落成一个脚本 `scripts/glance.py`，再加上 B 站要登录才能拿字幕的取法。脚本不带参数运行就打印帮助。

## 本机事实（2026-10-31 核验）

- 依赖：`python -m pip install -U yt-dlp imageio-ffmpeg`。ffmpeg 用 imageio_ffmpeg 自带的 exe，不要求系统装 ffmpeg；当天 yt-dlp 是 2026.10.26。
- B 站的视频信息接口和 720p 纯视频流不登录就能拿到；字幕的下载地址必须登录才给。
- Windows 上的 Chrome 给 cookie 加了应用绑定加密，yt-dlp 的 `--cookies-from-browser chrome` 读不出来，所以 B 站字幕改在用户浏览器的页面里取，见下文。
- 当天经本机代理连 YouTube，curl 和 yt-dlp 都在 SSL 握手阶段被断开（Google 正常），YouTube 这条路**未验**。

## 处方

1. **先看元数据**：`python glance.py meta <URL>`，拿到标题、时长、简介、分 P、章节和字幕清单。章节和简介往往已经给出结构。
2. **文字轨**（主要信息来源）：
   - B 站：按下面「B 站字幕」拿到字幕 JSON 的地址，然后 `python glance.py subs "<地址>" sub.txt`。地址自带 auth_key，在本机直接下载即可，不需要 cookie。
   - YouTube 等站点：`fetch` 会顺带下载字幕（`--sub-langs`），再用 `subs xxx.vtt sub.txt` 转成纯文本。自动字幕逐行滚动产生的重复行会被去掉。
   - 完全没有字幕时再考虑 Whisper 本地转写（本机有 RTX 4070 Ti SUPER，但 faster-whisper 没装、这条路没验过）。转写前先问用户值不值得：几十分钟的视频要下载音频，还要装模型。
   - 字幕一般几十 KB，用 Read 分段读完，不要只读开头就下结论。
3. **画面轨**（字幕说不出来的东西：价格、型号、表格、代码、图表）：`python glance.py fetch <URL> <目录>` 下载 720p 纯视频流，再按视频类型选抽帧方式：
   - **有固定版式卡片的视频**（测评、教程、榜单）：先抽一两帧找目录或索引页，拿到每一段的时间点；再用 `frames --at <时间点列表> --offset 4 --crop ... --tile 2x11`，只裁出关心的区域拼成总览图。实测 64 张参数卡拼成 3 张图就读完了。
   - **不知道画面里有什么**：用 `frames --max 12 --tile 4x3` 按场景切换均匀抽帧，先看一张总览图，再决定要不要细抽。
   - 总览图里帧的顺序是按行从左到右；`index.tsv` 记着每个序号对应的时间点。
4. **合成总结**：结论以字幕为主，数字以画面为准。截不到的卡片（那一刻画面切到了主持人）要写明，不要用推测补上。

## B 站字幕

需要用户已在浏览器里登录 B 站。用 Claude in Chrome（或任何能在页面里执行 JS 的浏览器工具）打开视频页，在页面里执行：

```js
const bv = 'BVxxxxxxxxxx', cid = <meta 打印的 cid>;
const r = await fetch(`https://api.bilibili.com/x/player/wbi/v2?bvid=${bv}&cid=${cid}`, {credentials: 'include'}).then(r => r.json());
({login: r.data?.login_mid, subs: (r.data?.subtitle?.subtitles || []).map(s => ({lan: s.lan, url: s.subtitle_url}))})
```

- `login` 为 0 说明没登录，此时字幕列表为空。
- `lan=zh` 等是 UP 主上传的人工字幕，优先用；`ai-zh` 是 B 站的 AI 字幕，没有人工字幕时用它。
- 这个接口不带 wbi 签名也能返回（2026-10-31 实测）；哪天被拒，就改在页面里读播放器自己发出的请求。
- 只读字幕，不在 B 站上点任何东西；用完关掉自己开的标签页。

## 坑

- 章节或索引页上的时间点常常落在转场上，加 `--offset 3~4` 才能落到卡片上。
- `--crop` 的格式是 `w:h:x:y`，坐标按缩放到 960 宽后的画面来量。先抽一整帧量好坐标，再批量裁。
- 场景模式在 68 分钟的视频里找到 307 处切换，用 `--max` 均匀抽稀，不要全部去看。
- 多 P 视频每一 P 有自己的 cid，字幕要分 P 取。

## 常用形态

```bash
G=<本 skill 目录>/scripts/glance.py
python $G meta "https://www.bilibili.com/video/BV1tCxk6PE9R"
python $G subs "https://aisubtitle.hdslb.com/bfs/...json?auth_key=..." sub.txt
python $G fetch "https://www.bilibili.com/video/BV1tCxk6PE9R" dl
python $G frames dl/video.mp4 f_index --at 1:58                      # 先找目录页
python $G frames dl/video.mp4 cards --at 3:12,4:24,1:02:08 --offset 4 \
  --crop 600:34:80:28 --crop 600:52:355:212 --tile 2x11              # 只裁型号名 + 价格
python $G frames dl/video.mp4 scene --max 12 --tile 4x3              # 不知道画面里有什么时
```

下载的视频和截出的帧放在临时目录（有 scratchpad 就放 scratchpad），不放进项目里。
