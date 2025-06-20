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

### 启动应用

在项目根目录下运行：

```bash
python -m vnag
```

### 初始化配置

1. 启动应用后，点击菜单栏中的"系统" → "连接"
2. 在弹出的对话框中配置：
   - **服务地址**：大模型API的base_url（如：https://api.openai.com/v1）
   - **API Key**：您的API密钥
   - **模型名称**：要使用的模型（如：gpt-3.5-turbo）
3. 点击"连接"完成初始化

### 开始对话

配置完成后，您就可以在输入框中输入问题，点击"发送请求"与AI进行对话了。

- 对话历史会自动保存在本地
- 支持Markdown格式的AI回复渲染
- 可以随时清空对话历史

## 项目结构

```
vnag/
├── vnag/                   # 核心模块
│   ├── __init__.py        # 版本信息
│   ├── __main__.py        # 应用入口
│   ├── gateway.py         # AI模型网关
│   ├── window.py          # 主窗口界面
│   ├── utility.py         # 工具函数
│   └── logo.ico          # 应用图标
├── pyproject.toml         # 项目配置
├── README.md             # 项目文档
└── LICENSE               # 开源协议
```

### 核心模块说明

- **gateway.py**：负责与各种大模型API的统一接口封装
- **window.py**：主窗口UI逻辑，包含聊天界面和配置对话框
- **utility.py**：提供JSON配置文件读写等工具函数
- **__main__.py**：应用启动入口，负责Qt应用初始化

## 开发状态

### 当前功能 ✅

- [x] 基础聊天UI界面
- [x] OpenAI兼容API支持
- [x] 对话历史管理
- [x] Markdown渲染
- [x] 配置持久化
- [x] 深色主题UI

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
