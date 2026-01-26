# Tool 工具系统

工具系统让 Agent 能够与外部世界交互。VNAG 支持本地工具和 MCP 工具两种类型。

## 工具类型

| 类型 | 说明 | 管理器 |
|------|------|--------|
| **本地工具** | Python 函数封装 | `LocalManager` |
| **MCP 工具** | 远程工具服务器 | `McpManager` |
| **Agent 工具** | Agent 封装的工具 | 直接注册到引擎 |

## LocalTool 本地工具

### 创建本地工具

```python
from vnag.local import LocalTool

def get_weather(city: str) -> str:
    """获取城市天气信息
    
    Args:
        city: 城市名称
    
    Returns:
        天气信息字符串
    """
    return f"{city}天气晴朗，温度25°C"

# 方式1：自动从函数提取信息
weather_tool = LocalTool(get_weather)

# 方式2：自定义名称和描述
weather_tool = LocalTool(
    function=get_weather,
    name="weather",                    # 自定义名称
    description="获取指定城市的天气",    # 自定义描述
    parameters={...}                   # 自定义参数 schema
)
```

### 工具命名规则

本地工具的名称格式为 `{模块名}_{函数名}`，其中下划线 `_` 会被替换为连字符 `-`：

```python
# 如果函数在 my_tools.py 模块中
def get_weather(city: str): ...

# 工具名称将是：my-tools_get-weather
```

### 注册工具

```python
# 方式1：通过引擎注册
engine.register_tool(weather_tool)

# 方式2：放置在 tools 目录自动加载
# 文件：tools/my_tools.py
# 或：vnag/tools/my_tools.py（内置工具所在目录）
```

### 自动加载

工具管理器会自动加载以下位置的工具：

1. `vnag/tools/*.py` - 内置工具
2. `tools/*.py` - 用户自定义工具（工作目录）

**自动加载示例**：

```python
# 文件：tools/calculator_tools.py

from vnag.local import LocalTool

def add(a: float, b: float) -> str:
    """两数相加"""
    return str(a + b)

def multiply(a: float, b: float) -> str:
    """两数相乘"""
    return str(a * b)

# 必须是 LocalTool 实例才会被加载
add_tool = LocalTool(add)
multiply_tool = LocalTool(multiply)
```

## LocalManager 本地工具管理器

```python
from vnag.local import LocalManager

manager = LocalManager()

# 注册函数
manager.register_function(my_function)

# 注册工具
manager.register_tool(my_tool)

# 列出所有工具
schemas = manager.list_tools()
for schema in schemas:
    print(f"{schema.name}: {schema.description}")

# 执行工具
result = manager.execute_tool("tool-name", {"arg1": "value1"})
```

## ToolSchema 工具定义

```python
from vnag.object import ToolSchema

schema = ToolSchema(
    name="get_weather",
    description="获取城市天气信息",
    parameters={
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市名称"
            },
            "unit": {
                "type": "string",
                "description": "温度单位",
                "enum": ["celsius", "fahrenheit"]
            }
        },
        "required": ["city"]
    }
)
```

### 参数类型映射

| Python 类型 | JSON Schema 类型 |
|-------------|------------------|
| `str` | `string` |
| `int` | `integer` |
| `float` | `number` |
| `bool` | `boolean` |
| `list` | `array` |
| `dict` | `object` |

## ToolCall 工具调用

当模型需要调用工具时，会返回 `ToolCall` 对象：

```python
from vnag.object import ToolCall

for delta in gateway.stream(request):
    if delta.calls:
        for call in delta.calls:
            print(f"ID: {call.id}")
            print(f"名称: {call.name}")
            print(f"参数: {call.arguments}")
```

## ToolResult 工具结果

工具执行后返回 `ToolResult`：

```python
from vnag.object import ToolResult

result = ToolResult(
    id="call_xxx",           # 关联的调用 ID
    name="get_weather",      # 工具名称
    content="北京天气晴朗",   # 执行结果
    is_error=False           # 是否出错
)
```

## McpManager MCP 工具管理器

### 配置 MCP 服务器

在 `.vnag/mcp_config.json` 中配置：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    }
  }
}
```

### 使用 MCP 管理器

```python
from vnag.mcp import McpManager

manager = McpManager()

# 列出工具
schemas = manager.list_tools()
for schema in schemas:
    print(f"{schema.name}: {schema.description}")

# 执行工具
result = manager.execute_tool("read_file", {"path": "test.txt"})
```

### MCP 工具命名

当 `mcp_config.json` **只配置了 1 个 MCP 服务**时，VNAG 会自动为工具名添加服务器名前缀，格式为 `{服务器名}_{工具名}`：

- `filesystem_read_file`
- `filesystem_write_file`
- `sequential-thinking_think`

当配置了**多个 MCP 服务**时，工具名以 MCP 服务器返回的原始名称为准（不添加前缀）。此时需要注意不同服务器之间可能存在的工具名冲突。

## 内置工具

VNAG 提供了多类内置工具：

### datetime_tools

```python
"datetime-tools_current-date"       # 当前日期
"datetime-tools_current-time"       # 当前时间
"datetime-tools_current-datetime"   # 当前日期时间
"datetime-tools_day-of-week"        # 星期几
```

### file_tools

```python
"file-tools_list-directory"   # 列出目录
"file-tools_read-file"        # 读取文件
"file-tools_write-file"       # 写入文件
"file-tools_delete-file"      # 删除文件
"file-tools_glob-files"       # 匹配文件
"file-tools_search-content"   # 搜索内容
"file-tools_replace-content"  # 替换内容
```

### network_tools

```python
"network-tools_ping"            # Ping 测试
"network-tools_telnet"          # 端口测试
"network-tools_get-local-ip"    # 本机 IP
"network-tools_get-public-ip"   # 公网 IP
"network-tools_get-mac-address" # MAC 地址
```

### code_tools

```python
"code-tools_execute-code"  # 执行 Python 代码
"code-tools_execute-file"  # 执行 Python 文件
```

### web_tools

```python
"web-tools_fetch-html"      # 获取网页 HTML
"web-tools_fetch-json"      # 获取 JSON 数据
"web-tools_fetch-markdown"  # 获取网页 Markdown（推荐优先使用）
"web-tools_check-link"      # 检查链接状态
```

### search_tools

联网搜索工具，需要在 `.vnag/tool_search.json` 中配置 API 密钥。

```python
"search-tools_bocha-search"   # 博查 Web Search API
"search-tools_tavily-search"  # Tavily Search API
"search-tools_serper-search"  # Serper Google 搜索 API
"search-tools_jina-search"    # Jina Search API
```

## 工具权限配置

文件系统工具需要权限配置：

**文件**：`.vnag/tool_filesystem.json`

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

## 最佳实践

### 1. 清晰的文档字符串

```python
def search_database(query: str, limit: int = 10) -> str:
    """在数据库中搜索信息
    
    根据查询条件搜索数据库，返回匹配的结果。
    
    Args:
        query: 搜索关键词或查询语句
        limit: 返回结果的最大数量，默认10条
    
    Returns:
        JSON 格式的搜索结果
    """
    ...
```

### 2. 返回字符串

```python
# 好：返回字符串
def get_count() -> str:
    return str(42)

# 不好：返回其他类型
def get_count() -> int:
    return 42
```

### 3. 处理异常

```python
def risky_operation(param: str) -> str:
    try:
        result = do_something(param)
        return str(result)
    except Exception as e:
        return f"错误: {str(e)}"
```

## 下一步

- [Message 消息](message.md) - 了解消息结构
- [教程 - 使用本地工具](../tutorial/local_tool.md) - 实践教程
- [教程 - 使用 MCP 工具](../tutorial/mcp_tool.md) - MCP 教程

