# Skill 速查手册

这份手册整理了今天导入到本地 Codex 的技能，方便后续快速判断“该用哪个 skill”以及“哪些 skill 可以联动使用”。

## 总览

| Skill | 核心用途 | 关键词 |
| --- | --- | --- |
| `agent-browser` | 用可访问性快照和 ref 做网页自动化 | 稳定交互、复杂页面、多步骤操作 |
| `browser-use` | 用 CLI 方式做浏览器自动化 | 打开网页、state、点击、输入、截图 |
| `skill-finder-cn` | 搜索和发现 ClawHub skills | 找 skill、搜索 skill、推荐 skill |
| `audit-website` | 审计网站 SEO、性能、安全、结构问题 | 网站体检、SEO 检查、上线前巡检 |
| `self-improving-agent` | 沉淀 learnings / errors / feature requests | 复盘、经验沉淀、持续改进 |
| `github` | 通过 `gh` CLI 操作 GitHub | issue、PR、Actions、API |
| `automation-workflows` | 设计业务自动化流程 | Zapier、Make、n8n、流程设计 |
| `generate-test-cases` | 从需求生成完整测试用例资产 | 测试设计、覆盖率、追溯、XMind |
| `prd-to-xmind-testcases` | 把 PRD 转成 XMind 测试大纲 | PRD、PDF、测试脑图、Markdown 导入 |

## 1. 网页自动化类

### `agent-browser`

- 核心用途：基于 accessibility tree snapshot 和 ref 做网页自动化。
- 更适合：
  - 多步骤网页流程
  - 复杂 SPA 页面
  - 需要稳定元素定位
  - 多 session 隔离
- 优点：
  - ref 选择更稳定
  - 适合复杂交互
- 适合搭配：
  - `automation-workflows`
  - `audit-website`
- 使用示例：
  - `使用 agent-browser 打开我的本地站点，完成登录并读取仪表盘上的关键数据`

### `browser-use`

- 核心用途：通过 `open -> state -> click/input` 的 CLI 工作流做浏览器自动化。
- 更适合：
  - 快速网页自动化
  - 表单填写
  - 截图
  - 页面状态读取
- 优点：
  - 命令流简单
  - 上手快
- 适合搭配：
  - `automation-workflows`
  - `audit-website`
- 使用示例：
  - `使用 browser-use 打开 https://example.com，截图并告诉我页面标题和主要按钮`

### `agent-browser` 和 `browser-use` 怎么选

- 想要更稳定的元素定位、复杂页面操作：选 `agent-browser`
- 想快速用 CLI 跑网页流程：选 `browser-use`

## 2. 网站质量与自动化类

### `audit-website`

- 核心用途：使用 `squirrel` CLI 审计网站质量。
- 关注点：
  - SEO
  - 性能
  - 可访问性
  - 结构化数据
  - 安全头 / HTTPS / 混合内容
- 典型场景：
  - 上线前巡检
  - 改版前后对比
  - 找 SEO / 技术质量问题
- 适合搭配：
  - `browser-use` / `agent-browser`：审计后复测关键页面
  - `github`：发现问题后回到仓库修复
  - `self-improving-agent`：记录审计经验
- 使用示例：
  - `使用 audit-website 审计 https://example.com，并按优先级列出最值得先修的问题`

### `automation-workflows`

- 核心用途：设计和优化自动化工作流。
- 关注点：
  - 找值得自动化的重复任务
  - 设计 trigger / conditions / actions
  - 在 Zapier / Make / n8n 之间选工具
  - 计算 ROI
- 典型场景：
  - 客户表单提交流程自动化
  - 报表发送自动化
  - 数据同步
  - 业务通知链路
- 适合搭配：
  - `browser-use` / `agent-browser`：把网页动作落地成自动化
  - `audit-website`：做网站定期巡检流程
  - `self-improving-agent`：沉淀自动化设计模式
- 使用示例：
  - `使用 automation-workflows 为“用户提交表单后自动建档、发欢迎邮件、通知销售”设计一套流程`

## 3. GitHub 与技能扩展类

### `github`

- 核心用途：通过 `gh` CLI 操作 GitHub。
- 关注点：
  - `gh issue`
  - `gh pr`
  - `gh run`
  - `gh api`
- 典型场景：
  - 看 issue / PR
  - 查 CI / Actions 失败
  - 做 GitHub API 查询
  - 处理仓库协作问题
- 适合搭配：
  - `generate-test-cases`：测试设计完成后落地到仓库
  - `audit-website`：把网站问题回流到代码和 PR
  - `self-improving-agent`：记录修复经验
- 使用示例：
  - `使用 github skill 查看 openai/openai 最近 10 个 PR，并标出 CI 失败的项`

### `skill-finder-cn`

- 核心用途：在 ClawHub 上搜索和推荐技能。
- 典型场景：
  - “有没有 skill 能做这个？”
  - “帮我找一个适合某个任务的 skill”
  - 想扩充本地技能库
- 适合搭配：
  - 所有 skill
- 角色定位：
  - 它不是执行器，是“找工具”的入口。
- 使用示例：
  - `使用 skill-finder-cn 帮我搜索适合“网页自动化测试”的 ClawHub skill`

## 4. 测试设计类

### `generate-test-cases`

- 核心用途：从需求文档和图片生成结构化测试用例，并导出 XMind。
- 强项：
  - EP / BVA / ST / EG 四种测试设计方法
  - 覆盖率检查
  - 优先级分布控制
  - 需求追溯
  - `.memory/` 持久化学习
  - XMind 导出
- 典型场景：
  - 正式测试设计
  - 长期维护的测试资产沉淀
  - 需求到测试用例的系统化转换
- 更适合：
  - 需要深度、质量门禁、历史学习能力的项目
- 适合搭配：
  - `prd-to-xmind-testcases`
  - `github`
  - `self-improving-agent`
- 使用示例：
  - `使用 generate-test-cases 读取 requirements 目录里的需求，生成测试用例并导出 XMind`

### `prd-to-xmind-testcases`

- 核心用途：把 PRD / PDF / docx / txt / md 快速转成 XMind 可导入 Markdown 大纲。
- 强项：
  - 输入格式支持广
  - 产出快
  - 适合需求评审前快速梳理测试脑图
  - 按需加载通用 / 接口 / 性能测试规范
- 典型场景：
  - 先出一版测试脑图
  - 把 PRD 快速变成结构化测试点
  - 前期测试评审
- 更适合：
  - 要快、要轻、先出导图轮廓
- 适合搭配：
  - `generate-test-cases`
- 使用示例：
  - `使用 prd-to-xmind-testcases 读取 requirements 里的 PRD，生成可导入 XMind 的 Markdown 测试大纲`

### `generate-test-cases` 和 `prd-to-xmind-testcases` 怎么选

- 要快、要轻、先从 PRD 变成测试导图：选 `prd-to-xmind-testcases`
- 要深、要完整、要追溯、要长期复用：选 `generate-test-cases`

## 5. 经验沉淀类

### `self-improving-agent`

- 核心用途：把错误、经验、改进点记录到 `.learnings/`。
- 记录内容：
  - `LEARNINGS.md`
  - `ERRORS.md`
  - `FEATURE_REQUESTS.md`
- 典型场景：
  - 解决了一个非显然问题
  - 用户纠正了方案
  - 某类 bug 反复出现
  - 某个工作流值得抽象成经验
- 适合搭配：
  - 所有 skill
- 角色定位：
  - 它不是“完成任务”的 skill，而是“把成果留下来”的 skill。
- 使用示例：
  - `使用 self-improving-agent 记录这次修复支付回调问题的 learnings，并整理到 .learnings/ERRORS.md`

## 典型组合用法

### 组合 1：PRD 到正式测试资产

1. `prd-to-xmind-testcases`
2. `generate-test-cases`
3. `github`
4. `self-improving-agent`

适用：
- 先快速把 PRD 转成测试脑图
- 再做深度测试设计
- 最后落地到仓库和测试代码

### 组合 2：网站质量治理

1. `audit-website`
2. `browser-use` 或 `agent-browser`
3. `github`
4. `self-improving-agent`

适用：
- 先审计站点
- 再复测关键页面
- 再进仓库修复问题
- 最后沉淀经验

### 组合 3：自动化流程建设

1. `automation-workflows`
2. `browser-use` 或 `agent-browser`
3. `self-improving-agent`

适用：
- 先设计自动化流程
- 再实现网页自动化部分
- 最后把方法沉淀下来

### 组合 4：继续扩展技能库

1. `skill-finder-cn`
2. 找到新 skill
3. 安装并试用
4. `self-improving-agent` 记录哪些 skill 真正有价值

## 最简选择指南

- 找新 skill：`skill-finder-cn`
- 网页自动化：`browser-use` / `agent-browser`
- 网站审计：`audit-website`
- GitHub 操作：`github`
- 自动化流程设计：`automation-workflows`
- PRD 转测试脑图：`prd-to-xmind-testcases`
- 深度测试设计与测试资产沉淀：`generate-test-cases`
- 经验复盘与学习闭环：`self-improving-agent`

## 一句话记忆版

- `skill-finder-cn`：找工具
- `browser-use` / `agent-browser`：动网页
- `audit-website`：查网站
- `github`：管仓库
- `automation-workflows`：设计流程
- `prd-to-xmind-testcases`：快速出测试脑图
- `generate-test-cases`：正式做测试资产
- `self-improving-agent`：把经验留下来
