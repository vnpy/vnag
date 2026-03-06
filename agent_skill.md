# Agent Skill 加载与使用方式：最终总结与落地指南

下面是基于我们整段对话整理出的「可直接用于功能开发」的设计参考文档，重点围绕：

- Skill 的加载方式全景
- Level 1 元数据（name + description）在上下文中的最佳放置方式
- MCP 场景下的 Skill 动态发现与工具调用关系
- 一套从简单到成熟的架构演进与实现建议

---

## 一、整体认知：从“把所有 Skill 塞进 System Prompt”到“工程化 Skill 管理”

### 不推荐的做法

- 直接把所有 Skill 的完整 metadata、指令内容硬编码到 System Prompt 中。
- 问题：
  - 占用大量上下文 token，扩展性差。
  - 新增/下线 Skill 必须改 Prompt 和代码。
  - 难以管理版本与权限。

### 推荐的总体思路

用「**插件化 Skill + 渐进披露 +（可选）Registry +（可选）MCP 工具层**」的组合方案：

1. **本地目录化 Skill**：`skills/xxx/SKILL.md`
2. **Level 1 元数据常驻**：会话初始化时将 `name + description` 注入系统级上下文
3. **Level 2/3 按需加载**：真正用到某个 Skill 时，再加载其完整指令和脚本
4. **（可选）Registry**：集中管理多服务/多团队的 Skill
5. **（可选）MCP**：统一外部工具协议，Skill 在其上编排工具

---

## 二、Skill 三层结构与上下文策略

### 1. 三个 Level 的含义

- **Level 1：元数据（常驻）**
  - 内容：`name`、`description`、必要的 tags 等极精简信息
  - 职责：告诉模型「你拥有哪些能力的大纲」
  - 上下文位置：**会话初始化时加入 System Prompt 或注册为工具描述**

- **Level 2：完整 Skill 指令（按需加载）**
  - 内容：整个 `SKILL.md` 的主体——详细步骤、约束、示例等
  - 职责：当模型决定使用该 Skill 时，为它提供「工作说明书」
  - 上下文位置：**只有被选中时，作为系统/工具级指令注入当前/后续轮次**

- **Level 3：脚本与外部资源（延迟执行）**
  - 内容：脚本（Python/Shell）、模版、参考文档等
  - 职责：由 Agent/工具执行具体逻辑，把结果返回给模型
  - 上下文位置：通常不直接写入 Prompt，而是以「工具调用结果」的形式进入对话

### 2. Level 1 元数据到底放哪？

**结论：**

- **必须在会话/Agent 初始化时加载到系统级上下文**
  - 方式一：放在 System Prompt 的一部分，如「可用技能目录」
  - 方式二：注册为底层 LLM API 的工具列表（tool schema 的描述字段）
- **不放在后续 User Prompt 中逐条追加**，原因：
  - 语义上是系统配置，不是用户发言。
  - 模型在第一轮就可能需要这些能力信息。
  - 重复发送会浪费 token，并让上下文混乱。

你可以把 Level 1 理解为「会话级常驻配置」，而不是「逐轮消息」。

---

## 三、几种主流 Skill 加载方式及适用场景

### 1. System Prompt 硬编码（只适合 Demo）

- 做法：所有 Skill 内容（包括详细说明）写在 System Prompt 中。
- 适用：PoC、小玩具、Skill ≤ 3–5 且基本不变的场景。
- 不适用于你希望做的「工程化功能开发」。

### 2. 插件化/可插拔 Skill 目录（强烈推荐起步方案）

**目录结构示意：**

```text
skills/
  pdf-processing/
    SKILL.md          # YAML frontmatter + Markdown 指令
    scripts/
    resources/
  excel-read/
    SKILL.md
  ...
```

**SKILL.md 示例（精简版）：**

```yaml
---
name: "pdf-processing"
description: "从 PDF 合同中提取关键条款并返回结构化结果。"
tags: ["pdf", "document", "contract"]
version: "1.0.0"
---
# 使用说明
1. 接收 PDF 文件路径或文件 ID
2. 使用内部脚本提取文本
3. 识别关键条款（名称、金额、日期、义务）
4. 输出 JSON 结构
```

**加载流程：**

1. Agent/服务启动：
   - 扫描 `skills/` 目录，读取每个 `SKILL.md` frontmatter。
   - 抽取 `name + description` → 构建一个 Skill 元数据列表（Level 1）。
2. 会话初始化：
   - 将该列表以「可调用技能目录」或「工具描述」方式加入系统级上下文。
3. 运行时：
   - 模型根据用户请求，选择可能相关的 Skill 名称。
   - 后端根据选中的 Skill，加载完整 `SKILL.md`（Level 2），作为额外系统指令注入。
   - 若 SKILL 中要求执行脚本，则触发脚本/工具（Level 3）。

**优点：**

- 新增 Skill = 新建目录 + 写 SKILL.md，无需改核心逻辑。
- 适合 Git 管理、代码评审、多人协作。
- 直接支持后续扩展到 Registry、MCP。

### 3. 渐进披露（Progressive Disclosure）——控制上下文成本的关键

概括来说：

- **常驻的只有 Level 1（元数据）** → System Prompt/工具描述。
- **按需加载 Level 2**：只在真正使用某 Skill 时加载它的详细说明。
- **延迟资源 Level 3**：只在实际执行到该步骤时读取脚本/文件。

这个模式解决：

- 「Skill 多到几十上百个，Prompt 装不下」的问题。
- 「想要很灵活地增加/下线 Skill，不想改核心 Prompt」的问题。

### 4. 中心化 / 联邦式 Skill Registry（做平台时需要）

适合你计划做「多应用、多团队共享 Agent 的平台」时使用：

- 提供：
  - Skill 注册接口：`/skills/register`
  - Skill 发现接口：`/skills?tag=pdf`
  - 权限控制（哪个租户/应用能用哪些 Skill）
  - 版本管理与灰度（beta/stable）
- 与本地插件式目录的关系：
  - 本地是**部署单元**；Registry 是**治理与发现单元**。
  - Agent 启动时向 Registry 拉取可用 Skill 列表，再决定加载哪些到本地/本会话。

---

## 四、MCP 场景：Skill 动态发现与工具调用的关系

这是你问得最多、也是最容易弄混的一块。

### 1. 两个不同层级：不要混在一起

- **上层（控制面）**：Skill 管理 / Registry / MCP 工具发现
  - 问题：系统「从哪儿知道」有哪些工具/技能可以用？
- **下层（数据面）**：LLM API 请求中的 `tools` 字段
  - 问题：这一轮请求中，**实际把哪些工具**暴露给模型使用？

你的「传统 MCP 工具调用」理解，主要在**下层**；我们讨论的 Skill 加载，是**上层**策略，负责决定下层该填什么。

### 2. MCP 工具发现的正确用法

**错误的直觉（我们已经排除）：**

> 先走一轮对话 → 再调用某个“工具发现工具” → 把返回的技能列表当成 User Prompt 发回给模型

这个做法的问题：

- 模型第一轮就可能需要外部能力，但第一轮它还不知道工具列表。
- 把技能列表当作 User 消息会混淆语义角色。
- 每轮重复发列表，极度浪费 token。

**合理做法：**

1. **会话创建 / Agent 启动阶段**（不一定在用户可见的第一轮）：
   - Agent 作为 MCP client，调用类似 `tools/list` 的接口。
   - 拿到 MCP server 暴露的工具元数据（name、description、输入 schema 等）。
2. Agent 把这些信息：
   - 映射/注册到自己的 Skill Registry 中（可以在内存里）。
   - 根据场景筛选出本会话可用的子集。
   - 以两种方式之一暴露给 LLM：
     - 注册为工具列表（tool schema → `tools` 字段）。
     - 同时/额外在 System Prompt 中，告知「你可以通过工具调用访问 xxx 能力」。

**关键点：**

- 对模型来说，它看到的只是「工具列表 + 描述」，本质上和你手动定义 tools 没区别。
- MCP 只是在 Agent ↔ 外部服务这一侧做了「发现 + 统一协议」；Skill 加载负责在 Agent ↔ 模型这侧决定**如何展示这些工具**。

### 3. 再次对齐你的疑问

> MCP 所提供的工具调用是在 User Prompt 的 tools 部分提交给大模型的，和这里提到的 skill 加载方式不太一样？

可以这样理解两者关系：

- **MCP 工具调用（你说的传统用法）：**
  - 定义：一次 HTTP 请求中，`tools` 字段的内容。
  - 粒度：单次请求，随时可变。
  - 模型视角：只知道「这次请求里有这些工具」。

- **Skill 加载 / Level 1 元数据管理：**
  - 定义：Agent 如何在更长生命周期（会话 / 进程）内管理「我有哪些能力」。
  - 粒度：会话级 / Agent 级。
  - 用途：决定在「本次请求的 tools 列表」里放什么，以及如何描述。

**一句话统一：**

> Skill / Registry / 渐进披露，决定**给这轮请求准备哪一批工具**；  
> MCP / `tools` 字段，仅仅是**把这批工具按协议送进 LLM**。

---

## 五、按你的需求可直接采用的设计方案（推荐实现路线）

### 阶段 1：实现本地插件化 + 渐进披露（无需 MCP）

1. 采用 `skills/xxx/SKILL.md` 的目录结构。
2. 定义统一的 YAML frontmatter（至少包含 `name`、`description`、tags、version）。
3. Agent 启动时扫描目录：
   - 把所有技能的 `name + description` 整合成一段「技能目录」字符串。
   - 或在框架层注册为工具描述（视你使用的 LLM API 而定）。
4. 会话创建时：
   - 将这段技能目录附加到 System Prompt（或对应的「工具说明」区域）。
5. 运行时：
   - 模型选择某个技能名。
   - 实现 Skill Manager 组件：根据技能名加载完整 SKILL.md，并作为新的系统/工具指令注入下一轮。

### 阶段 2：引入 MCP 做外部能力统一封装

1. 搭建 MCP server，暴露业务 API、数据库、文件系统等为 MCP tools。
2. Agent 作为 MCP client：
   - 启动时 `tools/list`，将结果作为「工具候选」映射到本地 Skill Registry。
   - 可以一部分技能来自本地目录，一部分来自 MCP。
3. Skill 文件（SKILL.md）中只描述：
   - 业务级目标与步骤。
   - 应该调用哪些 MCP 工具（以名字指代）。
4. 这样你可以：
   - 在不改 Skill 的前提下，演进 MCP server 的实现。
   - 在不动 MCP 细节的前提下，新增高阶业务 Skill。

### 阶段 3：做平台时增加 Registry 层

1. 抽出独立的 Skill Registry 服务：
   - 用于多项目、多团队共享 Skill。
2. Agent 在会话创建时：
   - 根据租户/用户/应用信息，向 Registry 查询「本会话可用 Skill 列表」。
   - 再将这些 Skill 的 Level 1 信息注入 System Prompt 或工具描述字段。
3. 继续维持渐进披露：
   - 只在真正使用某个 Skill 时，加载它的完整定义与执行逻辑。

---

## 六、你在设计时可以直接记住的几条「关键规范」

1. **Level 1 元数据（name + description）属于系统级上下文：**
   - 在会话/Agent 初始化时注入。
   - 不随着 User 消息乱跑，更不通过「工具调用结果 → User Prompt」的方式回填。

2. **MCP 工具发现（tools/list）只在 Agent ←→ MCP 之间进行：**
   - 用户与模型对话的那一侧，只看到「已经筛选好的工具/Skill」。

3. **一次请求中的 `tools` 字段只是「呈现给模型的当前可用子集」：**
   - 实际可用的全球工具集合由 Skill Registry / MCP discovery 决定；
   - 对于模型，是被动接受你这次请求里给它看的那一部分。

4. **不要把「发现技能列表」当作一个普通工具调用的输出再发给模型当 User 消息：**
   - 这会使「系统配置」和「用户发言」角色混淆。

5. **推荐优先做好的两件事：**
   - 本地插件化技能目录（可测试、可版本控制）。
   - 完整实现渐进披露（Level 1 常驻，Level 2/3 按需加载）。

---

如果你接下来愿意细化到具体技术栈（例如 Java/Spring AI、Python + LangChain/FastAPI、Node.js 等），可以在这个文档基础上，把每层（Skill Manager、MCP Client、Registry）拆成具体模块与接口设计，直接落到工程实现。