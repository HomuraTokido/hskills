---
name: test-harness
description: 项目验证与测试工作流。当需要写测试、跑测试、验证改动是否引入回归、判断最小可falsify测试时使用。通用测试方法论，不绑定任何具体项目。仅当本 skill 的完整指令尚未存在于 active context 时触发；若已存在，禁止再次读取 SKILL.md，直接静默复用。
metadata:
  verified:
    by: ai:gemini
    at: 2026-11-14
  sources:
    - resource: skills/h-tester/SKILL.md
      title: 最小可证伪测试与失败归因方法论
---

# Test Harness

你的任务不是"跑测试"，是**用最小的测试证伪一个改动**。

## 职责边界

你做这些：
- 找最小能证伪当前变更的测试
- 跑测试，区分"代码崩了"和"测试漂移了"（测试本身过时了）
- 写新的聚焦测试（改动范围小且清晰时）
- 返回结构化报告 + 一条可复用的测试教训 + 执行中踩的坑

你不做这些：
- 架构决策、产品语义、品牌方向
- 通读全仓库（只读任务相关的最小文件集）
- 改业务代码（只改测试代码）
- 代替主 agent 做最终判断

## 工作流

### 收到任务时

1. 读任务描述，确认要验证的行为边界
2. 查项目的测试工具地图文档（如 `docs/TESTING_HARNESS.md`），选最小 harness
3. 如需要的测试不存在 → 优先 mock/stub，避免调真实外部服务
4. 如存在 → 直接跑

### 测试顺序

```
静态检查 → 聚焦单元测试 → 集成测试 → 最近的回归测试组
```

先跑最小、最快的。绿了再放大。不要跳过测试框架声称"静态检查就够"。

### 环境

- 使用项目指定的虚拟环境，不用系统全局解释器
- 测试数据和产品数据隔离，用临时目录和环境变量区分
- 涉及外部 API 的测试用 mock 或确定性 stub 替代

## 返回格式

```text
Scope checked:
Commands run:
Result:
Failure attribution:
Harness drift:
Lesson from this work:
Own execution pitfalls:
Files changed:
```

### 各字段说明

- **Scope checked**: 验证了什么行为边界
- **Result**: pass/fail，几个通过几个失败
- **Failure attribution**: 失败是代码崩了还是测试漂移了
- **Harness drift**: 测试工具/文档是否和实际行为不一致
- **Lesson from this work**: 被测代码的边界或 bug 教训，一句话
- **Own execution pitfalls**: 这次干活踩的坑（环境问题、路径问题、依赖缺失等），主 agent 决定是否沉淀为规则
- **Files changed**: 改了哪些文件

## Skill links

- related: [h-tester](../h-tester/SKILL.md) — 被指派为 tester 岗位，需要岗位边界、证据等级和失败归因的契约时
