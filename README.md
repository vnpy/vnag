# VNAG - Your Agent, Your Data.

<p align="center">
    <img src ="https://img.shields.io/badge/version-0.0.1-blueviolet.svg"/>
    <img src ="https://img.shields.io/badge/platform-windows|linux|macos-yellow.svg"/>
    <img src ="https://img.shields.io/badge/python-3.10|3.11|3.12|3.13-blue.svg" />
    <img src ="https://img.shields.io/github/license/vnpy/vnag.svg?color=orange"/>
</p>

VeighNa Agent (vnag) 是一款专为AI Agent开发而设计的Python框架，致力于为开发者提供简洁、强大且易于扩展的Agent构建工具。秉承"Your Agent, Your Data"的理念，vnag让您能够完全掌控自己的AI Agent和数据流程。

## 项目介绍

vnag是VeighNa团队推出的全新AI Agent开发框架，旨在降低AI Agent开发的门槛，让更多开发者能够快速构建属于自己的智能助手。

### 核心特点

- **🎯 专注于Agent开发**：专门为AI Agent应用场景设计的框架架构
- **🔌 统一API接口**：支持OpenAI兼容的各种大模型API
- **🎨 现代化UI**：基于PySide6的美观用户界面
- **📝 智能对话**：支持Markdown渲染的聊天界面
- **💾 数据管控**：本地化的对话历史和配置管理
- **🔧 易于扩展**：清晰的模块化架构，便于二次开发

### 适用场景

- AI聊天机器人开发
- 智能客服系统
- 知识问答助手
- 个人AI助理
- 企业内部智能工具

## 环境准备

### 系统要求

- **操作系统**：Windows 11、Linux (Ubuntu 22.04+)、macOS 10.14+
- **Python版本**：Python 3.10 或更高版本（推荐使用Python 3.13）
- **内存要求**：建议8GB以上

### 依赖组件

- **PySide6**：现代化的Qt GUI框架
- **OpenAI**：大模型API调用库
- **Markdown**：文本渲染支持

## 安装步骤

### 从源码安装

1. 克隆项目到本地：
```bash
git clone https://github.com/vnpy/vnag.git
cd vnag
```

2. 安装依赖：
```bash
pip install -e .
```

## 快速开始

### 运行脚本测试（临时）

说明：当前 UI 仍在调整中，暂不支持 `python -m vnag` 启动。请先拉取 main 分支代码并通过 script 目录中的测试脚本进行验证。

示例（在项目根目录执行）：

```bash
# 分段器示例
python vnag/script/run_markdown_segmenter.py
python vnag/script/run_python_segmenter.py
python vnag/script/run_cpp_segmenter.py
```

# 完整RAG项目流程demo

   fork api_agent项目代码，切到vnag_rag_demo目录运行测试脚本：

 - 知识库导入（MD/PY/CPP 批量入库 + 计时）
   ```
   python run_add_document.py
   ```

 - 发送消息与对比（带RAG / 不带RAG 对比输出）
   ```
   python run_send_message.py
   ```

提示：上述 demo 默认使用本仓库附带的模板与示例路径，可根据本机数据调整脚本中的路径变量。

## 项目结构

```
vnag/
├── vnag/                       # 核心模块
│   ├── __init__.py            # 版本信息
│   ├── object.py              # 数据对象（Segment/Message/Request等）
│   ├── segmenter.py           # BaseSegmenter 与通用装箱逻辑
│   ├── segmenters/            # 分段器实现
│   │   ├── markdown_segmenter.py
│   │   ├── python_segmenter.py
│   │   └── cpp_segmenter.py
│   ├── vector.py              # BaseVector 接口
│   ├── vectors/               # 向量库实现
│   │   └── chromadb_vector.py
│   ├── gateways/              # 网关实现集合（OpenAI 等兼容实现）
│   └── utility.py             # 工具函数（读写文件/临时目录等）
├── vnag/script/               # 快速测试脚本集合（run_*.py）
├── pyproject.toml             # 项目配置
├── README.md                  # 项目文档
└── LICENSE                    # 开源协议
```

### 核心模块说明

- **segmenters/**：Markdown/Python/C++ 分段器（Python/C++ 为 AST 结构化切分，统一装箱）
- **vectors/chromadb_vector.py**：ChromaDB 向量存储（CPU 友好，内部DB分批写入）
- **gateways/openai_gateway.py**：OpenAI 兼容网关（流式输出）
- **utility.py**：读写 JSON/文本、临时目录管理等
- **script/**：分段器/入库/发送消息测试脚本

## 开发状态

### 当前功能 ✅

- [x] 分段器：Markdown（按标题）、Python（AST）、C++（libclang AST）
- [x] 向量库：ChromaDB 集成（内部DB分批写入，避免单批上限）
- [x] 网关：OpenAI 兼容，支持流式回答
- [x] 脚本：批量入库（MD/PY/CPP）、RAG 与不带 RAG 的对比发送

### 暂未开放 ⏳

- [ ] UI 启动（`python -m vnag` 尚未开放，UI 正在调整）
- [ ] 插件系统、多 Agent 会话、文件上传、主题等增强

### 开发路线图 🚧

- [ ] 插件系统架构
- [ ] 多Agent会话管理
- [ ] 文件上传支持
- [ ] 自定义提示词模板
- [ ] 对话导出功能
- [ ] 更多UI主题选择
- [ ] MCP服务扩展支持

## 贡献代码

我们欢迎所有形式的贡献！无论是bug报告、功能建议还是代码贡献。

### 开发流程

1. Fork本项目
2. 创建您的功能分支：`git checkout -b feature/AmazingFeature`
3. 提交您的更改：`git commit -m 'Add some AmazingFeature'`
4. 推送到分支：`git push origin feature/AmazingFeature`
5. 提交Pull Request

### 代码规范

项目使用以下工具确保代码质量：

- **Ruff**：代码格式化和linting
- **MyPy**：静态类型检查

在提交代码前，请运行：

```bash
# 代码检查
ruff check .

# 类型检查
mypy vnag
```

### 问题反馈

如果您遇到任何问题或有建议，请通过以下方式联系我们：

- 在GitHub上提交[Issue](https://github.com/vnpy/vnag/issues)
- 发送邮件至：xiaoyou.chen@mail.vnpy.com

## 版权说明

本项目采用MIT开源协议，详情请参阅[LICENSE](LICENSE)文件。

---

**立即开始您的AI Agent开发之旅！🚀**
