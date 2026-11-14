---
name: skill-creator
description: 在 HSkills 里新建、重写、裁决或审查任何 skill 之前先读。定义 frontmatter 契约、正文写法、Skill links 约定和 lint 流程。日常写 skill 用这个；要跑 eval 或优化 description 触发率时转 anthropic-skills:skill-creator。
metadata:
  verified:
    by: human:homura
    at: 2026-09-02
  sources:
    - resource: codex skill-creator SKILL.md（~/.codex/skills/.system/skill-creator）
      title: 四条原则、目录结构、命名、quick_validate 白名单
    - resource: anthropic skill-creator SKILL.md（claude-plugins-official/plugins/skill-creator）
      title: 三层加载、500 行经验值、写前四问、写法风格
    - resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf
      title: OKF v0.2 SPEC.md：frontmatter 只放可查询字段；verified / sources 核验语义（注：同栈 hwiki 知识页采用更早期的最小子集 OKF v0.1 加 admission 扩展）
---

# skill-creator

HSkills 是所有 skill 的唯一权威源。这里写的 skill 会分发到每个 agent，所以按这份约定写，写完过 lint。

## 原则（取自 codex skill-creator）

- **假定 agent 已经能干。** 只写会改变它决策的东西。通用建议、重复说明、猜测的边界情况、不澄清任务的例子，都删。
- **保住用户的意图和范围。** skill 支持被要求的任务，不替换用户的选择、不扩大任务、不暗示额外的外部动作权限。一次失败或个人偏好不升成普适规则。
- **具体程度和风险匹配。** 多种做法都合理时留给 agent 选。只在正确性、安全、权限或确实脆弱的流程需要时，才写死步骤、脚本或绝对语气。
- **发现要便宜且准。** name 和 description 在 skill 加载前就可见。写实际能力和适用时机；排除项只在能防止误路由时加。不写穷举式能力清单。

再加一条 HSkills 自己的：**文档有的放指针，文档没有的进 skill。** 工具自带的帮助（`-h`、官方页面、程序内帮助）只写一行指向。skill 装的是实测的坑、本机事实、处方、常用形态。

## 基线：裸 skill 目录

HSkills 要在 Codex、Claude Code 和其他宿主上都能用，所以只假设所有宿主的最小公约数：一个目录、一个 SKILL.md、frontmatter 里 name 和 description。宿主自己的加成（catalog 卡、语义检索等）是那个宿主的适配层，从文件里再算一遍，不反过来定义文件。文件是唯一保证跟着走的东西，所以出处、核验、链接都写在文件里。

## 两类 skill

- **自己写的**（everything、h-* 岗位、skill-creator 等）：字节归我们，按本文全部规则走。
- **有上游的**（按需从外部引入的第三方 skill，如 tavily、playwright、review-agent 等；公开仓默认不打包第三方镜像，`cards/` 初始为空）：**字节归上游，一个都不改**，也不加 metadata，不写封皮，不重写 description。更新走整目录覆盖：拉上游克隆、diff、覆盖。判断标准只有一条：有没有一个能指回去的上游。它的资料卡在 `cards/<name>.md`，见下。

## 资料卡：cards/<name>.md

上游 skill 进不了文件的东西记在卡上。Markdown 加 YAML frontmatter，和 SKILL.md 同一种文本形态，但不是 skill。

```yaml
---
skill: review-agent                       # 等于文件名，等于 skills/ 下的目录名
upstream: https://github.com/openai/codex  # 上游仓库
path: codex-rs/skills/src/assets/samples/review-agent   # 仓库内路径
commit: 83a4187837                        # 本地这份对应的上游 commit
clone: ~/upstream/openai-codex             # 可选本机字段；填写后 lint 才比对本地克隆
verified: {by: human:<owner>, at: 2026-09-02}
links:                                    # 想给它挂的 Skill links，写在卡上不写进文件
  - type: related
    target: test-harness
    when: "报告的缺陷或测试缺口需要行为验证时"
---
正文放不成字段的东西：本机事实、同名不同物的提醒、为什么选这个上游。
```

lint 对有卡的 skill 不查 description、metadata 和顶层键，仅在 `clone` 非空时检查 `skills/<name>/` 是否与 `clone/path` 一致（忽略 CRLF 和尾空格）；未填 `clone` 时跳过本地比对且不报 warning。文件里若有 Skill links 段会警告要求挪到卡上。卡上的 links 参与链接图。卡放仓库根的 `cards/`，不放 skill 目录里，因为更新是整目录覆盖，目录里的东西会被覆盖掉。自己写的 skill 不发卡，出处留在文件的 metadata 里，跟着文件走。

## 结构

```
skills/<name>/
  SKILL.md        必需。frontmatter + 正文
  scripts/        可选。会被反复重写的逻辑，或需要确定性执行的操作
  references/     可选。只在特定情形才需要的材料，从 SKILL.md 指过去并说明何时读
  assets/         可选。进入产出物的文件，不当指令加载
```

不放 README、安装说明、changelog。宿主对已挂载的热层 skill（见 `hotlist.md`）按三层加载：name 加 description 常驻每个会话，正文在触发时进 context，scripts 和 references 按需读取；未挂载进宿主目录的冷层 skill 零常驻，靠检索按需读取。anthropic 的经验值是正文 500 行以内，接近时把条件性内容分到 references。

## 命名

- 不占基础名。`pdf`、`notion`、`web-research` 这种名字盘上一个名字底下能有五家的东西，占了就是主动排进撞车队列。
- 自己写的、带归属的岗位类 skill 用 `h-` 前缀（H 是「マスター」的命名空间），如 `h-web-researcher`。
- 岗位类 skill 用 researcher 不用 research：岗位有归属、汇报格式和边界，"事"没有。归属写在正文第一段，不写进 description。
- 有上游的 skill 保持上游名。

## Frontmatter

| 键 | 必填 | 约束 |
|---|---|---|
| `name` | 是 | 等于目录名；小写字母、数字、连字符；64 字内 |
| `description` | 是 | 中文。写做什么和什么时候用，1024 字内，不含尖括号。按冷热分写法，见下 |
| `allowed-tools` `user-invocable` `disable-model-invocation` `license` `compatibility` | 否 | 宿主专用，原样透传 |
| `metadata` | 否 | 自由袋。第三方导入的原样保留当出处证据。HSkills 自己用两个子键，见下 |

description 的两种写法，取决于这个 skill 在 `hotlist.md` 里是不是热层：

- **热层**（常驻 context，极少数）：读者是触发判断。按 anthropic 的建议写得推一点，把会引起它的用户说法列出来，因为常驻 skill 的失败模式是该触发没触发。
- **冷层**（默认，靠 search 工具找）：读者是搜索。写能力和适用场景的关键词，让人和搜索都能按词命中；不写推的措辞，冷层不存在少触发的问题。

冷热变动先改 `hotlist.md`，description 随之改写。

codex 和 anthropic 的校验器都拒绝白名单以外的顶层键，所以 HSkills 的字段一律放在 `metadata` 下：

```yaml
metadata:
  verified:            # 人工核验。by 用 human: 前缀，at 用 ISO 日期。语义同 OKF v0.2
    by: human:<owner>
    at: 2026-09-02
  sources:             # 本版从哪些变体裁决而来。每项至少有 resource
    - resource: <路径、URL 或 path@commit>
      id: <hash，可选>
      title: <一句话，可选>
```

其他顶层键 lint 报 warning。遗留的 `version` `description_zh` `tools` `platforms` 在该 skill 下次重写时处理，不单独整改。

## 写法

- 写之前回答四个问题：让 agent 能做什么；什么时候触发；输出什么形状；要不要测试用例。答不出前两个就先别写。
- 解释为什么，少用 MUST。祈使句。
- 本机事实必须带核验日期，写成「本机事实（YYYY-MM-DD 核验）」，与 `metadata.verified.at` 一致。
- 断言写进去之前在本机跑过。跑不了的标"未验"。
- 推荐段落顺序：本机事实 → 处方 → 坑 → 常用形态 → 完整参考 → Skill links。不强制，缺的段省略。

## Skill links

段落标题固定 `## Skill links`，每行一条：

```
- <type>: [Title](../<name>/SKILL.md) — 何时顺着这条链接走
```

| type | 方向 | 说明 |
|---|---|---|
| `parent` | 单向声明 | 上级，最多一个。同级和 child 由脚本从 parent 反推，不手写 |
| `related` | 对称 | 双方都应声明。缺回链 lint 报出，再补 |
| `dispatch` | 单向 | 满足条件时转交对方 |
| `alternative` | 单向 | 同一目的的替代方案 |

`child` 是遗留类型，lint 警告，改成对方声明 parent。链接目标必须存在于 `skills/`。

宿主适配层可把 Skill links 的标题和说明用作检索词（incoming link terms）；具体索引规则由宿主维护，不改变这里的链接约定。

## 流程

1. 新建或重写：先按本文写草稿；裁决多个变体时，先按 hash 去重再语义比较，重写往往比选一个好。
2. 跑断言。
3. `python skills/skill-creator/scripts/lint_skills.py`，error 清零。
4. 需要时 `--index --write` 重新生成 `INDEX.md`，它是派生物，不手改。
5. 要 eval 或 description 优化，转 `anthropic-skills:skill-creator`，它有对照跑和 `improve_description.py`。

## 脚本

- `scripts/lint_skills.py`：检查以上规则。`--stats` 按行数和 description 长度排序打印，供人看尾部；`--index` 生成索引，`--write` 落盘。
- `scripts/scan_variants.py`：用 es.exe 找一个 skill 在全盘的所有副本，按归一化 hash 分变体、按目录性质分类，裁决前先跑它。仅 Windows。
- `scripts/stamp.py`：把 `metadata.verified` / `sources` 写进自己写的 skill 的 frontmatter，不碰其余字节。有上游的 skill 不用它。默认校验人由 `HSKILLS_VERIFIER` 指定，未设时为 `human:owner`。`--by human:<owner>` 要多加 `--human-confirmed`，只在ta明确确认过这一版时加；agent 自己核过的写 `--by ai:<模型名>`。
- `scripts/pack.py`：不带参数只打印用法；`--build` 把 hotlist 里标 web 的 skill 打成 claude.ai 能传的 zip（`build/web/`）；`--check` 拿 Claude 桌面端缓存的账号副本和 HSkills 比对，报告网页端是否落后。网页端没有 CLI，只能手动删旧传新。仅 Windows。
- 脚本对缺失字段跳过、未知字段忽略。改字段名时文件和脚本同一个 commit 一起改，不做兼容层。

## 样例

`skills/everything/SKILL.md` 是第一个按本约定写的 skill；本文件是第二个。
