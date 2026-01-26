# 常见问题 (FAQ)

本页面收集了使用 VNAG 过程中的常见问题和解决方案。

## 安装问题

### ModuleNotFoundError: No module named 'vnag'

**问题描述**：运行示例脚本时提示找不到 vnag 模块。

**解决方案**：

1. 确保在项目根目录下执行命令
2. 确保已激活虚拟环境
3. 使用可编辑模式安装：

```bash
pip install -e .
```

### pip 安装速度慢

**问题描述**：使用 pip 安装依赖时速度很慢。

**解决方案**：使用国内镜像源：

```bash
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
```

或配置永久镜像源：

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### PySide6 安装失败

**问题描述**：安装 PySide6 时出错。

**解决方案**：

1. 确保 Python 版本 >= 3.10
2. 尝试单独安装：

```bash
pip install pyside6
```

3. Windows 用户可能需要安装 Visual C++ Redistributable

## API 配置问题

### API 请求失败

**问题描述**：调用大模型 API 时报错。

**解决方案**：

1. 检查 `.vnag/connect_xxx.json` 配置文件
2. 确认 API Key 正确且未过期
3. 确认 Base URL 正确
4. 检查网络连接

```json
{
    "api_key": "sk-your-correct-key",
    "base_url": "https://api.openai.com/v1"
}
```

### 模型列表为空

**问题描述**：UI 中模型下拉框为空。

**解决方案**：

1. 检查是否已配置 API 服务
2. 验证 API Key 是否正确
3. 某些 API 不支持列出模型，需要手动输入模型名称

## MCP 工具问题

### npx 不是内部或外部命令

**问题描述**：运行 MCP 相关功能时提示 npx 不存在。

**解决方案**：

1. 安装 Node.js LTS 版本：https://nodejs.org/
2. 确保 Node.js 添加到系统 PATH
3. 验证安装：

```bash
npx --version
```

### MCP 工具列表为空

**问题描述**：没有加载到任何 MCP 工具。

**解决方案**：

1. 检查 `.vnag/mcp_config.json` 是否存在
2. 验证配置格式正确：

```json
{
  "mcpServers": {
    "服务器名": {
      "command": "npx",
      "args": ["-y", "包名", "参数"]
    }
  }
}
```

3. 确保 npx 可以正常执行配置的命令

### MCP 工具调用超时

**问题描述**：MCP 工具首次调用很慢或超时。

**解决方案**：

这是正常现象。MCP 服务器通过 npx 启动时，首次需要下载和安装依赖包，可能需要几十秒。后续调用会快很多。

## 文件系统工具问题

### 没有权限访问文件

**问题描述**：文件系统工具提示没有权限。

**解决方案**：

在 `.vnag/tool_filesystem.json` 中配置允许访问的路径：

```json
{
    "read_allowed": [
        "/path/to/allowed/read/dir"
    ],
    "write_allowed": [
        "/path/to/allowed/write/dir"
    ]
}
```

## RAG 问题

### ChromaDB 初始化失败

**问题描述**：使用 ChromaDB 时报错。

**解决方案**：

1. 确保已安装 chromadb：

```bash
pip install chromadb
```

2. 检查持久化目录是否可写

### 向量维度不匹配

**问题描述**：搜索时报向量维度错误。

**解决方案**：

确保索引和查询使用相同的嵌入器和模型：

- OpenAI text-embedding-3-small: 1536 维
- OpenAI text-embedding-3-large: 3072 维
- Sentence Transformers MiniLM: 384 维

### C++ 分段器找不到 libclang

**问题描述**：使用 C++ 分段器时报错找不到 libclang。

**解决方案**：

1. 安装 LLVM/Clang
2. 确保系统能找到 libclang 动态链接库
3. Windows 用户将 LLVM 的 bin 目录添加到 PATH

## UI 问题

### UI 无法启动

**问题描述**：运行 Chat UI 时闪退或报错。

**解决方案**：

1. 确保已安装 PySide6：

```bash
pip install pyside6
```

2. 检查 Python 版本是否 >= 3.10

### 工具调用失败

**问题描述**：在 UI 中工具调用报错。

**解决方案**：

1. 检查工具是否正确配置在 Profile 中
2. 点击菜单查看追踪日志了解详细错误
3. 确认 MCP 服务器配置正确（如果使用 MCP 工具）

### 消息显示异常

**问题描述**：消息内容显示不正确或格式混乱。

**解决方案**：

1. 检查消息是否包含特殊字符
2. 尝试刷新界面
3. 重启应用

## 项目配置问题

### 如何为不同项目使用不同配置？

**解决方案**：

在项目目录下创建 `.vnag` 文件夹，程序会优先使用当前目录的配置：

```bash
cd my_project
mkdir .vnag
# 在此目录下添加配置文件
```

### Agent 和 Profile 保存在哪里？

**解决方案**：

所有配置保存在 `.vnag` 目录下：

- Profile: `.vnag/profile/`
- Session: `.vnag/session/`
- Log: `.vnag/log/`（追踪日志）

可以直接编辑 JSON 文件或通过 UI 管理。

## 其他问题

### 如何自定义本地工具？

**解决方案**：

1. 创建 Python 函数
2. 使用 LocalTool 包装
3. 注册到引擎

```python
from vnag.local import LocalTool

def my_tool(param: str) -> str:
    """工具描述"""
    return f"结果: {param}"

tool = LocalTool(my_tool)
engine.register_tool(tool)
```

或放置在 `tools/` 目录下自动加载。

### 如何查看调试日志？

**解决方案**：

1. 打开运行目录下的 `.vnag/log/` 目录
2. 找到当前会话对应的 `{session_id}.log` 文件

### 如何报告 Bug？

**解决方案**：

在 GitHub 上提交 Issue：https://github.com/vnpy/vnag/issues

请提供：
1. 问题描述
2. 复现步骤
3. 错误信息
4. 环境信息（Python 版本、操作系统等）

