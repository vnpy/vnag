# 使用本地工具

本地工具让 Agent 能够调用 Python 函数来执行具体任务。本教程将介绍如何使用内置工具和创建自定义工具。

## 内置本地工具

VNAG 提供了多类内置工具：

### 日期时间工具 (datetime_tools)

| 工具名称 | 说明 |
|----------|------|
| `datetime-tools_current-date` | 获取当前日期（YYYY-MM-DD） |
| `datetime-tools_current-time` | 获取当前时间（HH:MM:SS） |
| `datetime-tools_current-datetime` | 获取当前日期和时间 |
| `datetime-tools_day-of-week` | 获取今天是星期几 |

### 文件系统工具 (file_tools)

| 工具名称 | 说明 |
|----------|------|
| `file-tools_list-directory` | 列出目录内容 |
| `file-tools_read-file` | 读取文件内容 |
| `file-tools_write-file` | 写入文件内容 |
| `file-tools_delete-file` | 删除文件 |
| `file-tools_glob-files` | 按模式匹配文件 |
| `file-tools_search-content` | 搜索文件内容 |
| `file-tools_replace-content` | 替换文件内容 |

:::{warning}
文件系统工具需要配置权限。请在 `.vnag/tool_filesystem.json` 中设置允许访问的路径。
:::

### 网络工具 (network_tools)

| 工具名称 | 说明 |
|----------|------|
| `network-tools_ping` | Ping 测试 |
| `network-tools_telnet` | 端口连通性测试 |
| `network-tools_get-local-ip` | 获取本机局域网 IP |
| `network-tools_get-public-ip` | 获取公网 IP |
| `network-tools_get-mac-address` | 获取 MAC 地址 |

### 代码执行工具 (code_tools)

| 工具名称 | 说明 |
|----------|------|
| `code-tools_execute-code` | 执行 Python 代码字符串 |
| `code-tools_execute-file` | 执行 Python 文件 |

:::{danger}
代码执行工具会在独立进程中运行代码，但没有沙箱隔离。请仅对可信代码使用。
:::

### Web 工具 (web_tools)

| 工具名称 | 说明 |
|----------|------|
| `web-tools_fetch-html` | 获取网页 HTML 内容 |
| `web-tools_fetch-json` | 获取并解析 JSON 数据 |
| `web-tools_check-link` | 检查链接状态 |

## 使用内置工具

### 示例：日期助手

```python
from vnag.utility import load_json
from vnag.gateways.openai_gateway import OpenaiGateway
from vnag.engine import AgentEngine
from vnag.object import Profile


def main():
    # 初始化
    setting = load_json("connect_openai.json")
    gateway = OpenaiGateway()
    gateway.init(setting)
    
    engine = AgentEngine(gateway)
    engine.init()
    
    # 查看可用工具
    print("可用工具：")
    for tool in engine.get_tool_schemas():
        print(f"  - {tool.name}: {tool.description}")
    print()
    
    # 创建使用日期工具的 Agent
    profile = Profile(
        name="日期助手",
        prompt="你是一个日期时间助手，可以帮用户查询日期相关信息。",
        tools=[
            "datetime-tools_current-date",
            "datetime-tools_current-time",
            "datetime-tools_day-of-week",
        ]
    )
    
    agent = engine.create_agent(profile)
    agent.set_model("gpt-4o-mini")
    
    # 测试工具调用
    print("问：今天是星期几？\n")
    for delta in agent.stream("今天是星期几？"):
        if delta.content:
            print(delta.content, end="", flush=True)
    print("\n")


if __name__ == "__main__":
    main()
```

## 创建自定义工具

### 方法一：使用 LocalTool 类

```python
from vnag.local import LocalTool


def calculate_bmi(weight: float, height: float) -> str:
    """计算身体质量指数 (BMI)
    
    Args:
        weight: 体重（千克）
        height: 身高（米）
    
    Returns:
        BMI 值和健康评估
    """
    bmi = weight / (height ** 2)
    
    if bmi < 18.5:
        category = "偏瘦"
    elif bmi < 24:
        category = "正常"
    elif bmi < 28:
        category = "偏胖"
    else:
        category = "肥胖"
    
    return f"BMI: {bmi:.1f}，体重状态：{category}"


# 创建工具
bmi_tool = LocalTool(calculate_bmi)

# 注册到引擎
engine.register_tool(bmi_tool)
```

### 方法二：自定义工具模块

在 `tools/` 目录下创建 Python 文件，工具会自动加载（用户自定义工具模块）。

**文件：`tools/health_tools.py`**

```python
from vnag.local import LocalTool


def calculate_bmi(weight: float, height: float) -> str:
    """计算身体质量指数 (BMI)"""
    bmi = weight / (height ** 2)
    if bmi < 18.5:
        return f"BMI: {bmi:.1f}，偏瘦"
    elif bmi < 24:
        return f"BMI: {bmi:.1f}，正常"
    elif bmi < 28:
        return f"BMI: {bmi:.1f}，偏胖"
    else:
        return f"BMI: {bmi:.1f}，肥胖"


def calculate_calories(weight: float, age: int, gender: str) -> str:
    """计算基础代谢率 (BMR)"""
    if gender.lower() in ["男", "male", "m"]:
        bmr = 88.362 + (13.397 * weight) + (4.799 * 170) - (5.677 * age)
    else:
        bmr = 447.593 + (9.247 * weight) + (3.098 * 160) - (4.330 * age)
    return f"基础代谢率: {bmr:.0f} 千卡/天"


# 导出工具实例（必须是 LocalTool 实例才会被自动加载）
bmi_tool = LocalTool(calculate_bmi)
calories_tool = LocalTool(calculate_calories)
```

### 工具函数要求

1. **类型注解**：参数和返回值应有类型注解
2. **文档字符串**：描述工具功能，AI 会根据描述决定何时使用
3. **返回字符串**：返回值应为字符串类型

```python
def example_tool(
    param1: str,        # 必需参数
    param2: int = 10    # 可选参数
) -> str:
    """工具功能描述（AI 会看到这个描述）
    
    Args:
        param1: 参数1的说明
        param2: 参数2的说明（默认值：10）
    
    Returns:
        返回结果的说明
    """
    return f"结果: {param1}, {param2}"
```

## 工具调用流程

当用户提问时，Agent 会：

1. 分析用户意图
2. 决定是否需要调用工具
3. 选择合适的工具并构造参数
4. 执行工具并获取结果
5. 基于结果生成回复

```
用户: "今天是星期几？"
     ↓
Agent: 需要查询日期 → 调用 datetime-tools_day-of-week
     ↓
工具返回: "星期三"
     ↓
Agent: "今天是星期三。"
```

## 文件系统工具权限配置

为了安全，文件系统工具需要配置允许访问的路径。

**文件：`.vnag/tool_filesystem.json`**

```json
{
    "read_allowed": [
        "/home/user/documents",
        "/home/user/projects"
    ],
    "write_allowed": [
        "/home/user/projects/output"
    ]
}
```

## 下一步

- [使用 MCP 工具](mcp_tool.md) - 连接更强大的远程工具
- [核心组件 - 工具系统](../components/tool.md) - 深入了解工具系统

