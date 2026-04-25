# 配置 Profile

Profile 是 Agent 的行为配置模板，定义了 Agent 的角色、能力和行为模式。本教程将详细介绍如何配置和管理 Profile。

## Profile 结构

```python
from vnag.object import Profile

profile = Profile(
    name="代码助手",                      # 必填：配置名称
    prompt="你是一个专业的代码助手...",    # 必填：系统提示词
    tools=["code-tools_execute-code"],    # 必填：可用工具列表（不需要工具时传 []）
    use_skills=True,                      # 可选：是否启用技能目录与 get_skill 工具
    temperature=1.0,                      # 可选：生成温度
    max_tokens=4096,                      # 可选：最大输出 token
    max_iterations=10,                    # 可选：最大工具调用轮次（默认 10）
    compaction_threshold=6000,            # 可选：输入 token 阈值，0 表示关闭
    compaction_turns=3                    # 可选：压缩后保留最近 3 轮
)
```

## 字段详解

### name（名称）

配置的唯一标识符，用于保存、检索和管理 Profile。

```python
profile = Profile(
    name="Python助手",  # 建议使用有意义的名称
    ...
)
```

### prompt（系统提示词）

系统提示词定义了 Agent 的角色、行为准则和回答风格。这是影响 Agent 表现最重要的配置。

**示例：通用助手**

```python
prompt = """你是一个乐于助人的 AI 助手。

请遵循以下原则：
1. 回答问题时简洁清晰
2. 如果不确定，请诚实说明
3. 在适当时候提供代码示例
"""
```

**示例：专业领域助手**

```python
prompt = """你是一个专业的金融分析师助手。

你的职责：
- 解答金融投资相关问题
- 分析市场趋势和数据
- 提供专业但易懂的建议

注意事项：
- 所有建议仅供参考，不构成投资建议
- 涉及具体投资决策时，建议咨询专业顾问
"""
```

### tools（工具列表）

指定 Agent 可以使用的工具。工具名称格式为 `模块名_工具名`。

```python
profile = Profile(
    name="全能助手",
    prompt="你是一个能够使用多种工具的助手。",
    tools=[
        # 日期时间工具
        "datetime-tools_current-date",
        "datetime-tools_current-time",
        "datetime-tools_day-of-week",
        
        # 文件系统工具
        "file-tools_read-file",
        "file-tools_write-file",
        "file-tools_list-directory",
        
        # 网络工具
        "network-tools_ping",
        "network-tools_get-public-ip",
        
        # 代码执行工具
        "code-tools_execute-code",
        
        # MCP 工具（需要配置 mcp_config.json）
        "filesystem_read_file",
    ]
)
```

:::{tip}
可以通过 `engine.get_tool_schemas()` 获取所有可用工具的列表。
:::

### temperature（生成温度）

控制输出的随机性，取值范围通常为 0-2。

需要注意的是，不同模型对温度参数的支持程度并不一致：有些模型允许自由调整，有些模型会固定使用 `1.0`，还有些模型可能直接忽略该参数。因此，是否调整温度应以目标模型和网关的实际行为为准。

| 值 | 特点 | 适用场景 |
|----|------|----------|
| 0-0.3 | 确定性高，输出一致 | 代码生成、事实问答（仅在模型支持调温时） |
| 0.5-0.7 | 平衡创意和一致性 | 通用对话（仅在模型支持调温时） |
| 0.8-1.2 | 更有创意和多样性 | 创意写作、头脑风暴（仅在模型支持调温时） |
| 1.3-2.0 | 高度随机 | 极端创意需求（仅在模型支持调温时） |

```python
# 代码助手：低温度，确保代码正确性（仅在模型支持调温时）
code_profile = Profile(
    name="代码助手",
    prompt="你是一个专业的程序员...",
    tools=["code-tools_execute-code"],
    temperature=0.2
)

# 创意写作：高温度，增加创意（仅在模型支持调温时）
writer_profile = Profile(
    name="创意写手",
    prompt="你是一个富有想象力的作家...",
    tools=[],
    temperature=1.0
)
```

### use_skills（启用技能）

启用后，Agent 会在系统提示词中看到技能目录，并可以通过 `get_skill` 工具按需加载完整技能内容。

```python
profile = Profile(
    name="研究助手",
    prompt="你是一个擅长联网调研的助手...",
    tools=["search-tools_search-web", "web-tools_fetch-markdown"],
    use_skills=True
)
```

如果你的任务依赖“先搜索再阅读”“带来源回答”“先澄清再行动”等工作流，建议优先开启该选项。

### max_tokens（最大输出）

限制单次回复的最大 token 数量。

```python
profile = Profile(
    name="摘要助手",
    prompt="请用简洁的语言总结内容...",
    tools=[],
    max_tokens=500  # 限制输出长度
)
```

### max_iterations（最大迭代）

当 Agent 需要多次调用工具时，限制最大调用轮次，防止无限循环。

```python
profile = Profile(
    name="研究助手",
    prompt="你是一个研究助手...",
    tools=["web-tools_fetch-html", "file-tools_write-file"],
    max_iterations=5  # 最多调用 5 轮工具
)
```

### compaction_threshold（压缩阈值）

当会话历史过长时，VNAG 可以先将旧消息总结为摘要，再继续发送请求。该字段用于设置触发压缩的输入 token 阈值。

压缩只影响后续请求的上下文构造，不会删除会话原始历史。

- `0`：关闭压缩
- 正整数：当最近一次请求的 `usage.input_tokens` 超过该值时触发压缩

纯 usage 方案会在请求完成后拿到真实输入 token，因此压缩判断会应用在下一次请求发送之前。

如果对话经常包含较长代码块、工具结果或知识库片段，建议先从 `4000` 到 `6000` 开始试用，再根据实际效果调整。

压缩摘要主要通过提示词中的长度约束控制，当前提示词会要求模型尽量在 `1024` token 以内完整写完。实际请求仍复用当前会话的 `max_tokens` 配置（如果有），不额外引入独立的摘要输出字段。

```python
profile = Profile(
    name="长对话助手",
    prompt="你是一个擅长长对话的助手...",
    tools=[],
    compaction_threshold=6000
)
```

### compaction_turns（保留轮数）

压缩发生后，保留最近多少轮完整对话参与后续请求，其余更早的消息会折叠进摘要中。

```python
profile = Profile(
    name="长对话助手",
    prompt="你是一个擅长长对话的助手...",
    tools=[],
    compaction_threshold=6000,
    compaction_turns=3
)
```

## 推荐配置示例

以下示例是推荐配置模板，适合直接复制到代码里使用，或通过 `engine.add_profile()` / UI 保存到本地 `.vnag/profile/`。仓库本身不内置这些 `.vnag/profile/*.json` 运行时文件。

### 强化搜索型 Profile

下面这类配置适合复杂搜索、事实核查、文档确认、多来源比对和带来源回答。相比普通联网研究配置，这一版更强调：

- 先规划再执行
- 默认走统一搜索入口
- 搜索后继续阅读正文
- 交叉验证多个来源
- 将证据整理为结构化最终回答

建议名称：`深度研究助手`

```python
research_profile = Profile(
    name="深度研究助手",
    prompt="""你是一个擅长复杂联网调研、事实核查和多来源证据整合的研究型助手。

你的核心目标是：
1. 对依赖外部、最新、可争议或需要引用来源的问题，优先通过搜索和阅读正文获取证据，而不是直接凭记忆作答。
2. 在信息搜集完成后，基于证据组织出清晰、可追溯、带来源、可供用户进一步核验的回答。
3. 尽量减少无效搜索、重复搜索，以及只看 snippet 就下结论的情况。

工作原则：
1. 如果答案已经可以完全从当前对话、已有工具结果或本地材料中得到，就不要为了形式继续联网搜索。
2. 如果问题依赖外部或最新信息，先规划，再搜索，再阅读正文，再整合结论。
3. 对复杂任务先给出简短计划，再分步骤执行；必要时维护待办，避免遗漏或重复劳动。
4. 默认优先使用 `search-tools_search-web` 发现候选来源。
5. 当问题明显需要“先搜再直接读正文”，或者你希望减少多步编排失败时，优先考虑 `search-tools_search-and-read`。
6. 搜索结果主要用于发现候选来源，不应直接作为最终证据。
7. 对重要结论，尽量继续阅读 2 到 3 个高相关来源的正文，并交叉验证。
8. 对关键链接可继续调用 `web-tools_fetch-markdown` 深读，不要只依赖 snippet 或组合工具返回的截断正文。
9. 如果来源冲突，要明确写出冲突点，并说明你更相信哪一个来源以及理由。
10. 如果现有证据不足，要明确说明不足，不要编造结论。
11. 对涉及新闻、公告、价格、政策、版本、市场变化、统计口径变化、时间窗口敏感结论等强时效性任务，应先判断时效性是否会显著影响结论；如果会，优先获取当前日期或当前日期时间，再据此制定搜索和判断来源时效性。

工具使用原则：
1. `search-tools_search-web` 是默认搜索入口；通常无需显式指定 provider。
2. 在 `provider="auto"` 模式下，搜索工具会优先尝试当前可用的 provider，并在必要时自动回退到其他可用 provider。
3. 只有在统一入口结果明显不足，或任务确实需要 provider 特性时，才考虑显式指定 provider。
4. `search-tools_search-and-read` 适合快速获得候选来源和正文，但不应替代对关键 URL 的进一步深读。
5. `web-tools_fetch-markdown` 适合对已知 URL 做进一步深读。
6. `web-tools_check-link` 只用于确认链接可访问性，不能替代正文阅读。
7. 对时间敏感任务，优先使用日期时间工具获取当前时间，再决定搜索范围、关键词和证据取舍。
8. 当问题范围不清、目标模糊、缺少关键约束时，应先澄清再继续。

技能使用原则：
1. 当任务依赖外部或最新信息时，优先加载并遵循 `search-then-read`。
2. 当需要基于证据组织最终回答时，优先加载并遵循 `answer-with-sources`。
3. 当问题范围不清或缺少关键信息时，优先加载并遵循 `clarify-before-action`。
4. 当任务包含多个明显步骤时，优先加载并遵循 `plan-and-track`。

最终回答要求：
1. 优先给出基于证据的结论，而不是泛泛总结。
2. 尽量指出关键信息来自哪里，并在回答末尾提供清晰的“参考资料/参考链接”部分，列出可供用户核验的来源链接。
3. 对关键结论，尽量将结论与对应来源建立可追溯关系；不要只写来源名称而不写链接。
4. 当结果中包含大量数据、多个对象、多维对比或较多事实点时，优先使用表格、列表、分组小节等结构化方式展示，帮助用户快速阅读和理解；如果不适合表格，再退回列表或分段结构化总结。
5. 明确区分：
   - 已确认事实
   - 来源共识
   - 来源冲突
   - 你的推断
6. 如果无法确认，就明确说明“不确定”或“当前证据不足”。
7. 除非用户明确要求修改文件、执行代码或做本地操作，否则优先专注于搜索、阅读、分析和总结。""",
    tools=[
        "search-tools_search-web",
        "search-tools_search-and-read",
        "web-tools_fetch-markdown",
        "web-tools_check-link",
        "interaction-tools_ask-user",
        "todo-tools_init-todos",
        "todo-tools_update-todos",
        "todo-tools_read-todos",
        "datetime-tools_current-date",
        "datetime-tools_current-datetime",
    ],
    use_skills=True,
    temperature=0.2,
    max_tokens=4000,
    max_iterations=18,
    compaction_threshold=6000,
    compaction_turns=4,
)
```

对普通联网研究场景，推荐优先暴露统一搜索入口，而不是同时把所有 raw search provider 都挂给模型。

## Profile 管理

### 通过引擎管理

```python
from vnag.engine import AgentEngine

# 添加配置
engine.add_profile(profile)

# 更新配置
profile.temperature = 1.0
engine.update_profile(profile)

# 获取配置
my_profile = engine.get_profile("代码助手")

# 获取所有配置
all_profiles = engine.get_all_profiles()

# 删除配置
engine.delete_profile("代码助手")
```

### 配置持久化

Profile 会自动保存到 `.vnag/profile/` 目录下，格式为 JSON 文件：

```json
{
    "name": "代码助手",
    "prompt": "你是一个专业的代码助手...",
    "tools": ["code-tools_execute-code"],
    "temperature": 1.0,
    "max_tokens": 4096,
    "max_iterations": 10,
    "compaction_threshold": 6000,
    "compaction_turns": 3
}
```

## 最佳实践

### 1. 编写清晰的系统提示词

```python
# 好的提示词
prompt = """你是一个专业的 Python 开发助手。

## 你的能力
- 编写和解释 Python 代码
- 调试和优化代码
- 推荐最佳实践

## 回答风格
- 代码示例优先
- 解释要简洁明了
- 遇到错误先分析原因

## 限制
- 只处理 Python 相关问题
- 不提供与编程无关的建议
"""

# 不好的提示词
prompt = "你是助手"  # 太简单，缺少指导
```

### 2. 按需配置工具

```python
# 只添加必要的工具
profile = Profile(
    name="日期助手",
    prompt="你是一个专门回答日期相关问题的助手。",
    tools=[
        "datetime-tools_current-date",
        "datetime-tools_day-of-week",
    ]
)

# 避免添加不相关的工具，可能导致误用
```

### 3. 为不同场景创建专门的 Profile

```python
# 客服场景
customer_service = Profile(
    name="客服助手",
    prompt="你是一个专业的客服代表...",
    tools=[],
    temperature=1.0  # 通用兼容设置；若模型支持调温，可按需调低
)

# 创意场景
creative_writer = Profile(
    name="创意助手",
    prompt="你是一个创意写作助手...",
    tools=[],
    temperature=1.0  # 通用兼容设置；若模型支持调温，可按需调整
)
```

## 下一步

- [使用本地工具](local_tool.md) - 学习如何让 Agent 使用本地工具
- [使用 MCP 工具](mcp_tool.md) - 连接远程工具服务器

