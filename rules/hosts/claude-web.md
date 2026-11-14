# claude.ai 网页端差量

网页端读不到本仓库，也没有引用机制。网页端每轮全文注入的是记忆里的 `/profile.md` 和 `/preferences.md`：`/profile.md` 的「纪律」一节和本文件、core 按意思对应，不逐字对齐，由网页端的 Claude 维护。这边的改动只在会改变网页端的做法时，把意思交给网页端 Claude，措辞由它定；只管 Claude Code 那边的改动不发过去。

## 记忆

- `/preferences.md` 是临时收件箱：ta说「记住」的纠正只会单向往那里写，里面的东西不永久持有。过账去向：任何宿主都成立的进 core，只在网页端成立的进本文件，关于ta本人的进 个人背景文档，只属于某个 skill 的进那个 skill；过账后同步 `/profile.md`「纪律」，再从 `/preferences.md` 删掉。

## 交付

- 一次性、当天过期的产出（如每日早报）做成自包含 HTML 文件发在对话里，不发布成 artifact 页面，免得堆在作品库里。
- 需要ta本地动手的交付（补丁、改仓库、git 操作）：连同文件附一段能直接粘贴给 agent 的 prompt，这类活ta交给本地 agent 做。
- 在对话里交付 skill 时给单个 SKILL.md 文件卡片，`.skill` 压缩包卡片ta那边装不了、至少不能一键装；多文件的 skill 走 `pack.py --build` 打包，ta在网页上删旧传新（见 `hotlist.md`）。
- 不主动提醒、主动建议，也不建定时或自动任务；没被要求时不自动生成图片。
