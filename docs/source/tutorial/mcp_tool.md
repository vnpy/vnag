# 使用 MCP 工具

MCP（Model Context Protocol）是一种标准化的工具协议，允许 Agent 连接远程工具服务器。本教程将介绍如何配置和使用 MCP 工具。

## 什么是 MCP

MCP 是由 Anthropic 提出的开放协议，用于标准化 AI 模型与外部工具、数据源的交互方式。相比本地工具，MCP 工具：

- 支持更复杂的功能
- 可以跨语言实现
- 社区提供了丰富的预构建服务器

## 前置要求

MCP 工具通过 `npx` 命令执行，需要安装 Node.js：

1. 下载 [Node.js LTS](https://nodejs.org/)
2. 验证安装：`npx --version`

## 配置 MCP 服务器

在 `.vnag/mcp_config.json` 中配置 MCP 服务器：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    }
  }
}
```

### 配置说明

| 字段 | 说明 |
|------|------|
| `mcpServers` | MCP 服务器配置字典 |
| 服务器名称（如 `filesystem`） | 自定义的服务器标识 |
| `command` | 启动命令（通常是 `npx`） |
| `args` | 命令参数 |

## 常用 MCP 服务器

### 1. 文件系统服务器

提供文件读写、目录操作等功能。

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
    }
  }
}
```

提供的工具：
- `read_file` - 读取文件
- `write_file` - 写入文件
- `list_directory` - 列出目录
- `create_directory` - 创建目录
- `move_file` - 移动/重命名文件

### 2. 顺序思考服务器

帮助 Agent 进行结构化的思考过程。

```json
{
  "mcpServers": {
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    }
  }
}
```

### 3. 搜索服务器

提供网络搜索功能。

```json
{
  "mcpServers": {
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "your-api-key"
      }
    }
  }
}
```

## 使用 MCP 工具

### 示例代码

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
    
    # 查看 MCP 工具
    mcp_schemas = engine.get_mcp_schemas()
    print("MCP 工具列表：")
    for name, schema in mcp_schemas.items():
        print(f"  - {name}: {schema.description}")
    print()
    
    # 创建使用 MCP 工具的 Agent
    profile = Profile(
        name="文件助手",
        prompt="你是一个文件管理助手，可以帮用户查看和操作文件。",
        tools=[
            "filesystem_list_directory",
            "filesystem_read_file",
        ]
    )
    
    agent = engine.create_agent(profile)
    agent.set_model("gpt-4o-mini")
    
    # 测试
    print("问：列出当前目录的文件\n")
    for delta in agent.stream("列出当前目录下的所有文件"):
        if delta.content:
            print(delta.content, end="", flush=True)
    print("\n")


if __name__ == "__main__":
    main()
```

### 工具命名规则

当 `mcp_config.json` 中**只配置了 1 个 MCP 服务**时，工具名称格式为 `{服务器名}_{工具名}`：

- 服务器名：配置文件中定义的名称
- 工具名：MCP 服务器提供的原始工具名

例如：
- `filesystem_read_file`
- `filesystem_list_directory`
- `sequential-thinking_think`

当配置了**多个 MCP 服务**时，工具名以 MCP 服务器返回的原始名称为准（不添加前缀）。

## 调试 MCP 工具

### 查看可用工具

```python
# 获取所有 MCP 工具
mcp_schemas = engine.get_mcp_schemas()

for name, schema in mcp_schemas.items():
    print(f"工具: {name}")
    print(f"描述: {schema.description}")
    print(f"参数: {schema.parameters}")
    print()
```

### 常见问题

**1. npx 不是内部或外部命令**

请安装 Node.js 并确保其在 PATH 中。

**2. MCP 工具列表为空**

- 检查 `mcp_config.json` 是否存在且格式正确
- 检查服务器是否能正常启动

**3. 工具调用超时**

某些 MCP 服务器首次启动较慢，这是正常的。

## 本地工具 vs MCP 工具

| 特性 | 本地工具 | MCP 工具 |
|------|----------|----------|
| 实现语言 | Python | 任意语言 |
| 部署方式 | 直接集成 | 独立进程 |
| 启动速度 | 快 | 较慢（需要启动服务） |
| 功能复杂度 | 适合简单任务 | 可以很复杂 |
| 社区支持 | 自行开发 | 丰富的预构建服务器 |

## 混合使用

可以同时使用本地工具和 MCP 工具：

```python
profile = Profile(
    name="全能助手",
    prompt="你是一个功能强大的助手。",
    tools=[
        # 本地工具
        "datetime-tools_current-date",
        "code-tools_execute-code",
        
        # MCP 工具
        "filesystem_read_file",
        "filesystem_write_file",
    ]
)
```

## 下一步

- [实现 RAG](rag.md) - 学习如何构建检索增强生成系统
- [核心组件 - 工具系统](../components/tool.md) - 深入了解工具架构

