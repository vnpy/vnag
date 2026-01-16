# VNAG 文档

<p align="center">
    <img src="https://img.shields.io/badge/version-0.7.0-blueviolet.svg"/>
    <img src="https://img.shields.io/badge/platform-windows|linux|macos-yellow.svg"/>
    <img src="https://img.shields.io/badge/python-3.10|3.11|3.12|3.13-blue.svg" />
    <img src="https://img.shields.io/github/license/vnpy/vnag.svg?color=orange"/>
</p>

**Your Agent, Your Data.**

VNAG (VeighNa Agent) 是一款专为 AI Agent 开发而设计的 Python 框架，致力于为开发者提供简洁、强大且易于扩展的 Agent 构建工具。秉承 "Your Agent, Your Data" 的理念，VNAG 让您能够完全掌控自己的 AI Agent 和数据流程。

---

## ✨ 核心特点

- 🤖 **可定制智能体** - 轻松创建和管理多个智能体，每个都可拥有独立的角色、能力和行为模式
- 🔧 **双核工具体系** - 同时支持简单易用的本地函数工具和功能强大的 MCP 远程工具
- 🔌 **统一 API 接口** - 支持 OpenAI 兼容的各种大模型 API
- 🎨 **现代化 UI** - 基于 PySide6 的图形化界面，不仅是聊天窗口，更是强大的智能体调试和管理工具
- 📝 **智能对话** - 支持 Markdown 渲染的聊天界面
- 💾 **数据管控** - 本地化的对话历史和配置管理
- 🧩 **易于扩展** - 清晰的模块化架构，便于二次开发

---

## 🚀 快速开始

```bash
# 克隆项目
git clone https://github.com/vnpy/vnag.git
cd vnag

# 安装依赖
pip install -e .

# 运行聊天 UI
python examples/ui/run_chat_ui.py
```

👉 [查看完整安装指南](getting_started/installation.md)

---

## 📚 文档导航

```{toctree}
:maxdepth: 2
:caption: 快速入门

getting_started/index
```

```{toctree}
:maxdepth: 2
:caption: 教程

tutorial/index
```

```{toctree}
:maxdepth: 2
:caption: 核心组件

components/index
```

```{toctree}
:maxdepth: 2
:caption: RAG 模块

rag/index
```

```{toctree}
:maxdepth: 2
:caption: 图形界面

ui/index
```

```{toctree}
:maxdepth: 2
:caption: 配置指南

configuration/index
```

```{toctree}
:maxdepth: 2
:caption: 高级用法

advanced/index
```

```{toctree}
:maxdepth: 1
:caption: 参考

api/index
faq
changelog
contributing
```

---

## 🎯 适用场景

- AI 聊天机器人开发
- 智能客服系统
- 知识问答助手
- 个人 AI 助理
- 企业内部智能工具

---

## 📖 更多资源

- [GitHub 仓库](https://github.com/vnpy/vnag)
- [问题反馈](https://github.com/vnpy/vnag/issues)
- [VeighNa 社区](https://www.vnpy.com)

