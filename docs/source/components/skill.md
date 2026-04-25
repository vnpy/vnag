# Skill 技能系统

技能系统让智能体能够按需加载专业操作指南，避免将所有指令写入系统提示词导致上下文膨胀。

## 概述

技能采用两级加载机制：

| 级别 | 内容 | 加载时机 |
|------|------|----------|
| **Level 1** | 技能名称 + 一句话描述 | 创建智能体时自动注入系统提示词 |
| **Level 2** | 完整的操作步骤和参考资料 | 智能体通过 `get_skill` 工具按需加载 |

在 `Profile` 中设置 `use_skills=True` 即可启用：

```python
from vnag.object import Profile

profile = Profile(
    name="全能助手",
    prompt="你是一个专业的开发助手。",
    tools=["file-tools_read-file", "file-tools_write-file"],
    use_skills=True  # 启用技能系统
)
```

## SKILL.md 技能文件

### 目录结构

技能文件统一命名为 `SKILL.md`，放置在工作目录的 `skills/` 下，支持子目录：

```
skills/
├── create-api/
│   ├── SKILL.md              # 技能定义文件
│   ├── templates/
│   │   └── api_template.py   # 代码模板
│   └── reference.md          # 参考文档
├── write-tests/
│   └── SKILL.md
└── deploy/
    └── SKILL.md
```

### 文件格式

每个 `SKILL.md` 由 YAML Frontmatter 和 Markdown 正文两部分组成：

```markdown
---
name: create-api
description: 创建标准的 RESTful API 接口，包含路由、参数校验和错误处理
metadata:
  author: team
  version: "1.0"
---

## 操作步骤

1. 读取 `templates/api_template.py` 获取代码模板
2. 根据用户需求修改模板中的路由和参数
3. 添加参数校验逻辑
4. 编写错误处理代码
5. 将生成的代码写入指定文件

## 注意事项

- 所有 API 必须包含请求参数校验
- 错误响应需要统一格式
- 参考 [API 规范](./reference.md) 获取更多细节
```

### Frontmatter 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | str | 是 | 技能名称，用于标识和检索 |
| `description` | str | 是 | 一句话描述，显示在 Level 1 目录中 |
| `metadata` | dict | 否 | 自定义元数据（如作者、版本等） |

### 路径自动转换

正文中引用的相对路径会被自动转换为绝对路径，支持三种模式：

1. **目录路径**：`scripts/`、`templates/`、`examples/`、`reference/` 开头的路径
2. **文档引用**：`see reference.md`、`read forms.md` 等自然语言引用
3. **Markdown 链接**：`[API 规范](./reference.md)` 格式的链接

## Skill 数据模型

```python
from vnag.skill import Skill

skill = Skill(
    name="create-api",                          # 技能名称
    description="创建标准的 RESTful API 接口",    # 技能描述
    content="## 操作步骤\n...",                   # 正文内容（经过路径转换）
    metadata={"author": "team"},                 # 自定义元数据
    skill_dir="/path/to/skills/create-api"       # 技能所在目录
)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | str | 技能名称 |
| `description` | str | 技能描述 |
| `content` | str | 正文内容（经过路径转换） |
| `metadata` | dict | 自定义元数据 |
| `skill_dir` | str | 技能文件所在目录的绝对路径 |

## SkillManager 技能管理器

`SkillManager` 负责技能的发现、加载和执行。

```python
from vnag.skill import SkillManager

manager = SkillManager()

# 扫描 skills/ 目录，加载所有 SKILL.md（支持递归子目录）
manager.load_skills()

# 查看已加载的技能列表
manager.list_skills()  # ["create-api", "write-tests", "deploy"]

# 获取 Level 1 技能目录文本（用于注入系统提示词）
catalog = manager.get_skill_catalog()

# 获取 get_skill 工具的 Schema（无技能时返回 None）
schema = manager.get_tool_schema()

# 执行 get_skill 工具，返回 Level 2 完整内容
content = manager.execute_tool("create-api")
```

`SkillManager` 在 `AgentEngine.init()` 时自动完成加载，通常不需要手动调用。

技能目录固定从工作目录下的 `skills/` 加载。若希望项目级技能随当前项目生效，应确保项目根目录存在 `.vnag/`，使该目录成为 `WORKING_DIR`。

### 技能目录输出示例

`get_skill_catalog()` 返回的文本会被追加到系统提示词末尾：

```
## 可用技能

你拥有以下专业技能，可在需要时通过 get_skill 工具加载完整操作指南：

- `create-api`: 创建标准的 RESTful API 接口，包含路由、参数校验和错误处理
- `write-tests`: 为现有代码编写单元测试
- `deploy`: 将应用部署到生产环境

使用方式：
1. 判断用户需求是否匹配某个技能
2. 调用 get_skill(skill_name="xxx") 加载完整操作指南
3. 严格按照技能指令执行任务
```

## 最佳实践

### 搜索工作流示例

对于需要联网查询的任务，可以提供一个聚焦“先搜索，再阅读正文”的技能，例如：

```markdown
---
name: search-then-read
description: 采用“先搜索、再阅读正文”的联网研究流程。适用于查询最新信息、外部事实、产品公告、官方文档、新闻动态或任何需要网页来源支持的问题。
---

1. 先调用搜索工具，不要直接凭记忆回答
2. 从结果中挑选 2 到 3 个高相关来源
3. 使用 `web-tools_fetch-markdown` 阅读正文
4. 对重要结论进行交叉验证
```

### 1. 聚焦具体任务

每个技能应对应一个明确的任务场景：

```markdown
# 好：聚焦具体任务
---
name: create-rest-api
description: 创建 RESTful API 接口
---

# 不好：范围过大
---
name: backend-development
description: 后端开发相关的所有任务
---
```

### 2. 描述清晰准确

`description` 是智能体判断是否调用技能的依据：

```markdown
# 好：明确说明用途
description: 为 Python 函数编写 pytest 单元测试，包含边界用例和 mock

# 不好：过于笼统
description: 写测试
```

### 3. 善用辅助资源

将代码模板、参考文档等放在技能子目录中，正文通过路径引用：

```markdown
---
name: create-component
description: 创建 React 组件
---

1. 读取 `templates/component.tsx` 获取组件模板
2. 读取 `reference.md` 了解项目组件规范
3. 根据用户需求修改模板
```

### 4. 写清前置工具和降级策略

如果某个技能强依赖特定工具，建议在正文中显式写出：

- 这个技能通常需要哪些工具
- 当前 Profile 若未启用这些工具时应如何处理

例如：

```markdown
## 前置工具

- `search-tools_search-web`
- `web-tools_fetch-markdown`

如果当前 Profile 未启用这些工具，应先提示用户切换到包含这些工具的 Profile，或修改当前 Profile 配置后再继续。
```

这样做可以降低“技能已经加载，但当前 Agent 实际无法执行该技能流程”的概率。

## 下一步

- [Tool 工具系统](tool.md) - 了解本地工具和 MCP 工具
- [Agent 智能体](agent.md) - 了解智能体的 Profile 配置
