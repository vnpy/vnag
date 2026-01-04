# 教程

本章节通过一系列循序渐进的教程，帮助您掌握 VNAG 的各项功能。

## 本章内容

```{toctree}
:maxdepth: 2

first_agent
profile
local_tool
mcp_tool
rag
chat_ui
```

## 教程概览

| 教程 | 难度 | 预计时间 | 说明 |
|------|------|----------|------|
| [创建第一个 Agent](first_agent.md) | ⭐ | 5 分钟 | 从零开始创建一个能对话的 Agent |
| [配置 Profile](profile.md) | ⭐ | 10 分钟 | 学习如何定制 Agent 的行为 |
| [使用本地工具](local_tool.md) | ⭐⭐ | 15 分钟 | 让 Agent 使用本地函数工具 |
| [使用 MCP 工具](mcp_tool.md) | ⭐⭐ | 15 分钟 | 连接 MCP 远程工具服务器 |
| [实现 RAG](rag.md) | ⭐⭐⭐ | 20 分钟 | 构建检索增强生成系统 |
| [使用图形界面](chat_ui.md) | ⭐ | 10 分钟 | 使用 Chat UI 管理和调试 Agent |

## 前置要求

在开始教程之前，请确保您已经：

1. 完成了 [安装指南](../getting_started/installation.md)
2. 配置了至少一个大模型 API 密钥
3. 阅读了 [核心概念](../getting_started/key_concepts.md)

## 示例代码

所有教程的完整示例代码都可以在 `examples` 目录中找到：

```
examples/
├── agent/          # Agent 相关示例
├── gateway/        # Gateway 示例
├── tool/           # 工具调用示例
├── rag/            # RAG 示例
├── segmenter/      # 分段器示例
├── vector/         # 向量库示例
└── ui/             # UI 示例
```

