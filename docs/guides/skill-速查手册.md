# Skill 速查手册

这份手册整理了当前常用的本地 Skills，方便快速判断“该用哪个 skill”以及“哪些 skill 可以联动使用”。

## 总览

| Skill | 核心用途 | 关键场景 |
| --- | --- | --- |
| `agent-browser` | 基于可访问性树和 ref 的网页自动化 | 复杂页面、稳定元素定位、多步骤操作 |
| `browser-use` | 轻量 CLI 网页自动化 | 打开页面、点击输入、截图采集 |
| `skill-finder-cn` | 搜索/发现可用 skills | 找 skill、对比 skill、补充技能库 |
| `audit-website` | 网站质量审计（SEO/性能/可访问性/安全） | 上线前体检、改版前后对比 |
| `ui-ux-pro-max` | UI/UX 方案评审与体验优化建议 | 视觉升级、交互优化、可用性改进 |
| `self-improving-agent` | 经验沉淀与错误复盘 | learnings/errors/feature requests 归档 |
| `github` | 通过 `gh` 处理 GitHub 协作 | issue、PR、Actions、API 查询 |
| `automation-workflows` | 自动化流程设计与优化 | Zapier/Make/n8n 流程搭建 |
| `generate-test-cases` | 深度测试用例设计与资产沉淀 | 覆盖率提升、方法论驱动测试设计 |
| `prd-to-xmind-testcases` | PRD 快速转 XMind 测试大纲 | 需求评审期快速产出测试脑图 |

## 1. 网页自动化类

### `agent-browser`
- 核心用途：高稳定网页自动化，适合复杂交互流程。
- 适合场景：多步骤业务流、复杂 SPA、需要稳定定位元素。
- 常见搭配：`automation-workflows`、`audit-website`。

### `browser-use`
- 核心用途：命令式快速自动化网页操作。
- 适合场景：表单填写、抓取页面状态、快速回归操作。
- 常见搭配：`automation-workflows`、`audit-website`。

### 如何选
- 追求稳定与复杂流程：选 `agent-browser`。
- 追求快速执行与轻量操作：选 `browser-use`。

## 2. 网站质量与体验优化类

### `audit-website`
- 核心用途：对网站进行 SEO、性能、可访问性、安全维度审计。
- 适合场景：上线前巡检、改版后验收、质量回归。
- 常见搭配：`browser-use` / `agent-browser` + `github` + `self-improving-agent`。

### `ui-ux-pro-max`
- 核心用途：对页面视觉层级、交互流程、可用性进行专业优化建议。
- 适合场景：
  - 首页/详情页改版
  - 交互动线梳理
  - 移动端体验优化
  - 组件与信息密度优化
- 常见搭配：`frontend-skill`、`audit-website`、`browser-use` / `agent-browser`。
- 示例：
  - `使用 ui-ux-pro-max 评审首页与商品详情页，给出视觉层级、交互反馈和移动端优化清单`。

### `automation-workflows`
- 核心用途：设计可复用的业务自动化流程。
- 适合场景：线索分发、通知链路、日报周报自动化。
- 常见搭配：`browser-use` / `agent-browser`、`self-improving-agent`。

## 3. 协作与能力扩展类

### `github`
- 核心用途：通过 `gh` 快速完成仓库协作操作。
- 适合场景：PR/Issue 处理、CI 失败排查、API 查询。

### `skill-finder-cn`
- 核心用途：搜索和发现可安装/可用的 skills。
- 适合场景：
  - “有没有 skill 可以做这个？”
  - “我想找一个用于 xx 的 skill”。

## 4. 测试设计类

### `generate-test-cases`
- 核心用途：基于需求进行系统化测试设计，并支持长期资产沉淀。
- 适合场景：正式测试设计、覆盖率治理、测试规范化。

### `prd-to-xmind-testcases`
- 核心用途：将 PRD/PDF/docx/md 等快速转为 XMind 测试大纲。
- 适合场景：需求评审期快速产出测试脑图。

### 如何选
- 快速脑图初稿：`prd-to-xmind-testcases`。
- 深度测试设计与沉淀：`generate-test-cases`。

## 5. 经验沉淀类

### `self-improving-agent`
- 核心用途：沉淀错误、修复经验、可复用方法。
- 适合场景：复杂故障闭环、重复问题复盘、流程优化总结。

## 典型组合

### 组合 A：PRD 到测试落地
1. `prd-to-xmind-testcases`
2. `generate-test-cases`
3. `github`
4. `self-improving-agent`

### 组合 B：网站质量治理
1. `audit-website`
2. `browser-use` / `agent-browser`
3. `github`
4. `self-improving-agent`

### 组合 C：自动化流程建设
1. `automation-workflows`
2. `browser-use` / `agent-browser`
3. `self-improving-agent`

## 最简选择指南

- 找新 skill：`skill-finder-cn`
- 网页自动化：`browser-use` / `agent-browser`
- 网站审计：`audit-website`
- UI/UX 设计优化：`ui-ux-pro-max`
- GitHub 协作：`github`
- 自动化流程设计：`automation-workflows`
- PRD 转测试脑图：`prd-to-xmind-testcases`
- 深度测试设计：`generate-test-cases`
- 经验复盘沉淀：`self-improving-agent`

## 一句话记忆卡

- `skill-finder-cn`：找工具
- `browser-use` / `agent-browser`：动网页
- `audit-website`：查网站
- `ui-ux-pro-max`：做界面与体验优化
- `github`：管仓库
- `automation-workflows`：设计自动化流程
- `prd-to-xmind-testcases`：快速出测试脑图
- `generate-test-cases`：系统化测试设计
- `self-improving-agent`：把经验沉淀下来
