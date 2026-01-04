# 自定义工具

本教程介绍如何创建自定义工具，扩展 Agent 的能力。

## 工具类型

VNAG 支持三种类型的自定义工具：

| 类型 | 说明 | 使用场景 |
|------|------|----------|
| LocalTool | Python 函数封装 | 简单的本地功能 |
| AgentTool | Agent 封装 | 复杂任务、多 Agent 协作 |
| 自动加载工具 | 放置在 tools 目录 | 持久化的工具集 |

## LocalTool

### 基本用法

```python
from vnag.local import LocalTool


def calculate_bmi(weight: float, height: float) -> str:
    """计算身体质量指数 (BMI)
    
    根据体重和身高计算 BMI 值。
    
    Args:
        weight: 体重，单位：千克
        height: 身高，单位：米
    
    Returns:
        BMI 值和健康评估
    """
    bmi = weight / (height ** 2)
    
    if bmi < 18.5:
        status = "偏瘦"
    elif bmi < 24:
        status = "正常"
    elif bmi < 28:
        status = "偏胖"
    else:
        status = "肥胖"
    
    return f"BMI: {bmi:.1f}，体重状态：{status}"


# 创建工具
bmi_tool = LocalTool(calculate_bmi)

# 注册到引擎
engine.register_tool(bmi_tool)
```

### 自定义工具属性

```python
bmi_tool = LocalTool(
    function=calculate_bmi,
    name="bmi-calculator",              # 自定义名称
    description="计算身体质量指数",       # 自定义描述
    parameters={                         # 自定义参数 schema
        "type": "object",
        "properties": {
            "weight": {
                "type": "number",
                "description": "体重（千克）"
            },
            "height": {
                "type": "number",
                "description": "身高（米）"
            }
        },
        "required": ["weight", "height"]
    }
)
```

### 工具函数要求

1. **类型注解**：参数应有类型注解
2. **文档字符串**：清晰描述功能，AI 会参考
3. **返回字符串**：返回值必须是字符串

```python
def good_tool(
    param1: str,           # 必需参数
    param2: int = 10       # 可选参数（有默认值）
) -> str:
    """工具功能描述
    
    详细说明工具的用途和行为。
    
    Args:
        param1: 参数1的说明
        param2: 参数2的说明，默认值为10
    
    Returns:
        返回结果的说明
    """
    result = do_something(param1, param2)
    return str(result)
```

## AgentTool

AgentTool 将一个 Agent 封装为可被其他 Agent 调用的工具。

### 创建 AgentTool

```python
from vnag.agent import AgentTool
from vnag.object import Profile

# 创建专门的 Profile
code_expert_profile = Profile(
    name="代码专家",
    prompt="""你是一个资深的 Python 开发专家。

你的职责：
- 分析代码问题
- 提供优化建议
- 编写高质量代码

回答风格：
- 专业、准确
- 给出代码示例
- 解释原理
""",
    tools=["code-tools_execute-code"],
    temperature=0.3
)

# 封装为工具
code_expert_tool = AgentTool(
    engine=engine,
    profile=code_expert_profile,
    model="gpt-4o",
    name="code-expert",
    description="调用代码专家分析和解决编程问题"
)

# 注册到引擎
engine.register_tool(code_expert_tool)
```

### 使用 AgentTool

```python
# 主 Agent 可以调用代码专家
main_profile = Profile(
    name="通用助手",
    prompt="""你是一个通用助手。
    
当遇到复杂的代码问题时，可以调用代码专家工具获取帮助。
""",
    tools=["agent_code-expert"]  # 使用 agent_ 前缀
)

main_agent = engine.create_agent(main_profile)
```

### 多 Agent 协作

```python
# 创建多个专家
research_expert = AgentTool(
    engine=engine,
    profile=research_profile,
    model="gpt-4o",
    name="research-expert",
    description="调用研究专家进行资料收集和分析"
)

writing_expert = AgentTool(
    engine=engine,
    profile=writing_profile,
    model="gpt-4o",
    name="writing-expert",
    description="调用写作专家进行文章撰写"
)

engine.register_tool(research_expert)
engine.register_tool(writing_expert)

# 主 Agent 可以调用多个专家
coordinator_profile = Profile(
    name="项目协调员",
    prompt="你是一个项目协调员，可以调用不同的专家完成任务。",
    tools=[
        "agent_research-expert",
        "agent_writing-expert"
    ]
)
```

## 自动加载工具

将工具文件放在 `tools/` 目录下，启动时会自动加载。

### 文件结构

将工具文件放在**当前工作目录**的 `tools/` 文件夹下（注意：不是 `.vnag/tools/`）：

```
{项目目录}/
└── tools/
    ├── math_tools.py
    ├── data_tools.py
    └── api_tools.py
```

### 工具文件示例

**文件**：`tools/math_tools.py`

```python
from vnag.local import LocalTool


def add(a: float, b: float) -> str:
    """两数相加
    
    Args:
        a: 第一个数
        b: 第二个数
    
    Returns:
        计算结果
    """
    return str(a + b)


def multiply(a: float, b: float) -> str:
    """两数相乘"""
    return str(a * b)


def divide(a: float, b: float) -> str:
    """两数相除"""
    if b == 0:
        return "错误：除数不能为零"
    return str(a / b)


def power(base: float, exponent: float) -> str:
    """幂运算"""
    return str(base ** exponent)


# 导出工具实例（必须是 LocalTool 才会被加载）
add_tool = LocalTool(add)
multiply_tool = LocalTool(multiply)
divide_tool = LocalTool(divide)
power_tool = LocalTool(power)
```

### 工具命名

自动加载的工具名称格式：`{模块名}_{函数名}`

例如 `math_tools.py` 中的 `add` 函数，工具名称为 `math-tools_add`。

## 错误处理

工具应妥善处理异常：

```python
def safe_tool(param: str) -> str:
    """带错误处理的工具"""
    try:
        result = risky_operation(param)
        return str(result)
    except ValueError as e:
        return f"参数错误: {e}"
    except ConnectionError as e:
        return f"连接失败: {e}"
    except Exception as e:
        return f"未知错误: {e}"
```

## 异步工具

对于需要异步操作的场景，可以在工具内部使用 asyncio：

```python
import asyncio


def async_tool(url: str) -> str:
    """异步工具示例"""
    async def fetch():
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.text()
    
    result = asyncio.run(fetch())
    return result
```

## 最佳实践

### 1. 清晰的文档

```python
def search_database(
    query: str,
    table: str = "default",
    limit: int = 10
) -> str:
    """在数据库中搜索记录
    
    根据查询条件在指定表中搜索数据。支持模糊匹配和精确查询。
    
    Args:
        query: 搜索关键词，支持通配符 * 和 ?
        table: 目标表名，默认为 "default"
        limit: 返回结果的最大数量，默认 10 条
    
    Returns:
        JSON 格式的搜索结果，包含匹配的记录列表
    
    Example:
        search_database("user*", table="users", limit=5)
    """
    ...
```

### 2. 参数验证

```python
def validate_and_process(data: str, format: str = "json") -> str:
    """带验证的工具"""
    # 验证参数
    if not data:
        return "错误：data 参数不能为空"
    
    if format not in ["json", "xml", "csv"]:
        return f"错误：不支持的格式 '{format}'，请使用 json/xml/csv"
    
    # 处理逻辑
    ...
```

### 3. 结构化输出

```python
import json


def get_user_info(user_id: str) -> str:
    """获取用户信息"""
    user = fetch_user(user_id)
    
    result = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "created_at": user.created_at.isoformat()
    }
    
    return json.dumps(result, ensure_ascii=False, indent=2)
```

## 下一步

- [自定义分段器](custom_segmenter.md) - 支持新的文档格式
- [思维链集成](thinking.md) - 利用模型的思考过程

