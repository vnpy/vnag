# 贡献指南

我们欢迎所有形式的贡献！无论是 Bug 报告、功能建议还是代码贡献。

## 开始之前

1. **阅读文档**：了解项目结构和设计理念
2. **查看 Issue**：检查是否有相关的讨论或已知问题
3. **创建 Issue**：对于新功能或重大更改，先创建 Issue 讨论

## 开发流程

### 1. Fork 项目

点击 GitHub 页面右上角的 Fork 按钮。

### 2. 克隆到本地

```bash
git clone https://github.com/your-username/vnag.git
cd vnag
```

### 3. 创建虚拟环境

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 4. 安装开发依赖

```bash
pip install -e .
pip install ruff mypy
```

### 5. 创建功能分支

```bash
git checkout -b feature/amazing-feature
```

### 6. 进行开发

编写代码、添加测试、更新文档。

### 7. 代码检查

```bash
# 代码格式和规范检查
ruff check .

# 类型检查
mypy vnag
```

### 8. 提交更改

```bash
git add .
git commit -m "feat: add amazing feature"
```

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `style:` 代码风格（不影响功能）
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具相关

### 9. 推送到远程

```bash
git push origin feature/amazing-feature
```

### 10. 创建 Pull Request

在 GitHub 上创建 PR，详细描述您的更改。

## 代码规范

### Python 风格

- 遵循 PEP 8
- 使用 Ruff 进行格式化和检查
- 使用类型注解

```python
def example_function(param1: str, param2: int = 10) -> str:
    """函数说明
    
    Args:
        param1: 参数1说明
        param2: 参数2说明
    
    Returns:
        返回值说明
    """
    return f"{param1}: {param2}"
```

### 文档字符串

使用 Google 风格的文档字符串：

```python
class ExampleClass:
    """类的简要说明
    
    详细说明（可选）。
    
    Attributes:
        attr1: 属性1说明
        attr2: 属性2说明
    """
    
    def method(self, arg: str) -> bool:
        """方法说明
        
        Args:
            arg: 参数说明
        
        Returns:
            返回值说明
        
        Raises:
            ValueError: 异常说明
        """
        pass
```

### 类型注解

所有公开 API 必须有类型注解：

```python
from typing import Any
from collections.abc import Generator

def process(
    data: list[str],
    options: dict[str, Any] | None = None
) -> Generator[str, None, None]:
    ...
```

## 提交 Pull Request

### PR 标题

使用清晰的标题描述更改：

- `feat: add OpenRouter gateway support`
- `fix: resolve MCP tool timeout issue`
- `docs: update installation guide`

### PR 描述

提供以下信息：

1. **更改说明**：做了什么更改
2. **动机**：为什么需要这个更改
3. **测试**：如何验证更改
4. **相关 Issue**：关联的 Issue 编号

### PR 检查清单

- [ ] 代码通过 Ruff 检查
- [ ] 代码通过 MyPy 类型检查
- [ ] 添加了必要的文档
- [ ] 更新了 CHANGELOG（如果需要）

## 问题反馈

### 报告 Bug

在 [GitHub Issues](https://github.com/vnpy/vnag/issues) 提交 Bug 报告，包含：

1. **问题描述**：清晰描述问题
2. **复现步骤**：如何复现问题
3. **预期行为**：期望的正确行为
4. **实际行为**：实际发生的情况
5. **环境信息**：
   - Python 版本
   - VNAG 版本
   - 操作系统

### 功能建议

提交功能建议时，说明：

1. **功能描述**：想要什么功能
2. **使用场景**：为什么需要这个功能
3. **可能的实现**：如果有想法的话

## 联系方式

- GitHub Issues: https://github.com/vnpy/vnag/issues
- 邮箱: contact@mail.vnpy.com

## 致谢

感谢所有贡献者的付出！

---

*祝您贡献愉快！🎉*

