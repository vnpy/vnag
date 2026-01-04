# 安装指南

本文档将指导您完成 VNAG 的安装过程。

## 系统要求

- **Python**: 3.10、3.11、3.12 或 3.13
- **操作系统**: Windows、Linux 或 macOS
- **Node.js**: 如需使用 MCP 工具，请安装 Node.js LTS 版本

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/vnpy/vnag.git
cd vnag
```

### 2. 创建虚拟环境（推荐）

为了保持项目依赖的隔离，强烈建议您使用 Python 虚拟环境。

::::{tab-set}

:::{tab-item} Windows
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\activate
```
:::

:::{tab-item} macOS/Linux
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate
```
:::

::::

### 3. 安装依赖

```bash
# 从源码安装项目及其依赖
pip install -e .
```

## 验证安装

安装完成后，您可以通过以下命令验证：

```bash
python -c "import vnag; print(vnag.__version__)"
```

如果输出版本号（如 `0.6.0`），则表示安装成功。

## 可选依赖

根据您的使用场景，可能需要安装额外的依赖：

### RAG 相关

推荐直接安装 RAG 相关的全套依赖：

```bash
pip install -e .[rag]
```

或者根据需要单独安装：

```bash
# Markdown 分段器依赖
pip install markdown-it-py

# C++ 分段器依赖 (需配合系统 LLVM)
pip install libclang

# ChromaDB 向量库
pip install chromadb

# Qdrant 向量库
pip install qdrant-client

# Sentence Transformers 本地嵌入
pip install sentence-transformers
```

### C++ 分段器

如需使用 C++ 代码分段器，请安装 LLVM/Clang：

- **Windows**: 下载 [LLVM 安装包](https://releases.llvm.org/)，并将 `bin` 目录添加到 PATH
- **macOS**: `brew install llvm`
- **Linux**: `sudo apt install libclang-dev`

### MCP 工具

MCP 工具通过 `npx` 命令执行，需要安装 [Node.js](https://nodejs.org/)：

1. 下载并安装 Node.js LTS 版本
2. 验证安装：`npx --version`

## 常见问题

### ModuleNotFoundError: No module named 'vnag'

请确保您已经：
1. 在项目根目录下执行安装命令
2. 已激活虚拟环境
3. 使用 `pip install -e .` 而不是直接运行脚本

### pip 安装速度慢

可以使用国内镜像源：

```bash
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 下一步

安装完成后，请继续阅读 [快速开始](quickstart.md) 来运行您的第一个 Agent。

