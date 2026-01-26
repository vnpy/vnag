# 配置 Profile

Profile 是 Agent 的行为配置模板，定义了 Agent 的角色、能力和行为模式。本教程将详细介绍如何配置和管理 Profile。

## Profile 结构

```python
from vnag.object import Profile

profile = Profile(
    name="代码助手",                      # 必填：配置名称
    prompt="你是一个专业的代码助手...",    # 必填：系统提示词
    tools=["code-tools_execute-code"],    # 必填：可用工具列表（不需要工具时传 []）
    temperature=0.5,                      # 可选：生成温度
    max_tokens=4096,                      # 可选：最大输出 token
    max_iterations=10                     # 可选：最大工具调用轮次（默认 10）
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

控制输出的随机性，取值范围 0-2：

| 值 | 特点 | 适用场景 |
|----|------|----------|
| 0-0.3 | 确定性高，输出一致 | 代码生成、事实问答 |
| 0.5-0.7 | 平衡创意和一致性 | 通用对话 |
| 0.8-1.2 | 更有创意和多样性 | 创意写作、头脑风暴 |
| 1.3-2.0 | 高度随机 | 极端创意需求 |

```python
# 代码助手：低温度，确保代码正确性
code_profile = Profile(
    name="代码助手",
    prompt="你是一个专业的程序员...",
    tools=["code-tools_execute-code"],
    temperature=0.2
)

# 创意写作：高温度，增加创意
writer_profile = Profile(
    name="创意写手",
    prompt="你是一个富有想象力的作家...",
    tools=[],
    temperature=1.0
)
```

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

## Profile 管理

### 通过引擎管理

```python
from vnag.engine import AgentEngine

# 添加配置
engine.add_profile(profile)

# 更新配置
profile.temperature = 0.8
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
    "temperature": 0.5,
    "max_tokens": 4096,
    "max_iterations": 10
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
    temperature=0.3  # 回答需要一致性
)

# 创意场景
creative_writer = Profile(
    name="创意助手",
    prompt="你是一个创意写作助手...",
    tools=[],
    temperature=0.9  # 需要创意多样性
)
```

## 下一步

- [使用本地工具](local_tool.md) - 学习如何让 Agent 使用本地工具
- [使用 MCP 工具](mcp_tool.md) - 连接远程工具服务器

