# 命令行界面

VNAG 提供了基于终端的命令行界面（CLI），让您无需图形环境也能完整使用 Agent 的所有功能。CLI 模式适合服务器、SSH 远程连接以及需要与脚本集成的场景。

## 启动方式

### 交互模式

```bash
python -m vnag.cli
```

启动后进入持续交互的终端界面，可以多轮对话、切换 Profile 和模型、管理会话。

### 非交互模式

```bash
python -m vnag.cli --task "你的问题或任务"
```

执行单次任务后自动退出，适合脚本集成和批量处理。

## CLI 配置

CLI 通过 `.vnag/cli_setting.json` 读取独立配置，网关连接参数则与图形界面共用同一套 `connect_*.json` 文件。

**文件**：`.vnag/cli_setting.json`

```json
{
    "gateway_name": "OpenAI",
    "profile_name": "助手",
    "model_name": "gpt-4o"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `gateway_name` | str | 网关类型，如 `OpenAI`、`Anthropic`、`DeepSeek` 等（默认 `OpenAI`） |
| `profile_name` | str | 启动时默认加载的 Profile 名称；未配置时自动使用第一个 Profile |
| `model_name` | str | 启动时默认使用的模型名称；未配置时沿用 Profile 默认值 |

网关连接参数（API Key、Base URL 等）的配置方式与图形界面完全相同，请参阅 [配置指南](../configuration/index.md#网关配置)。

## 界面说明

启动交互模式后，终端界面包含以下元素：

```
  ✻ VeighNa Agent
  Profile: 助手
  Model:   gpt-4o
  Session: 20240115_103000_123456
  输入 /help 查看命令

You › _                                    [底部状态栏]
  助手  │  gpt-4o  │  msgs: 0
```

| 元素 | 说明 |
|------|------|
| 欢迎信息 | 显示当前 Profile、模型、会话 ID |
| `You › ` | 输入提示符，绿色加粗 |
| 底部状态栏 | 实时显示当前 Profile、模型名称和消息轮数 |

## 对话交互

在 `You › ` 提示符后直接输入内容并按 `Enter` 发送。AI 响应以流式方式实时输出：

- **思考链**：显示 `⏵ Thinking…` 后跟随灰色思考内容（若模型支持）
- **正文内容**：直接输出 AI 回答
- **工具调用**：显示 `⟡ 执行工具: <名称>` 及执行结果（`✓` 成功 / `✗` 失败）
- **警告/错误**：以黄色 `⚠` 或红色 `✗` 前缀显示

每轮结束后输出分隔线。按 `Ctrl+C` 可中止当前生成。

## 输入增强功能

### 历史记录

使用 `↑` / `↓` 方向键翻阅历史输入记录，历史保存在临时目录的 `cli_history.txt` 文件中，跨会话持久保留。

### 自动补全

按 `Tab` 键触发补全：

- **斜杠命令补全**：输入 `/` 后按 `Tab`，列出所有可用命令
- **文件路径补全**：输入 `@` 后按 `Tab`，补全当前工作目录下的文件/目录路径（目录以 `/` 结尾）

## 斜杠命令参考

以 `/` 开头的输入会被识别为命令，不会发送给 AI。

| 命令 | 说明 |
|------|------|
| `/help` | 显示所有可用命令列表 |
| `/clear` | 清空终端屏幕 |
| `/model` | 查看当前模型名称 |
| `/model <name>` | 切换到指定模型，并持久化到 `cli_setting.json` |
| `/profile` | 查看当前 Profile 名称 |
| `/profile <name>` | 切换到指定 Profile（创建新会话），并持久化到 `cli_setting.json` |
| `/retry` | 重发上一轮用户输入（弹出最近一轮消息后重新提交） |
| `/sessions` | 列出所有会话，当前会话以 `→` 标记 |
| `/title` | 调用 AI 自动为当前会话生成标题并重命名 |
| `/stats` | 显示当前会话的消息数和会话 ID |
| `/exit` | 退出 CLI（等同于 `Ctrl+D`） |

## 非交互模式详解

```bash
python -m vnag.cli --task "用一句话介绍 Python"
```

- 使用 `cli_setting.json` 中配置的 Profile 和模型
- 执行完任务后自动退出，退出码为 0
- 输出内容与交互模式相同（支持流式渲染）
- 适合在 Shell 脚本或 CI/CD 流程中调用

**示例：将输出重定向到文件**

```bash
python -m vnag.cli --task "总结以下内容：$(cat report.txt)" > summary.txt
```

## 故障排除

### 终端显示乱码

确认终端编码为 UTF-8，并使用支持 Rich 样式的终端（如 Windows Terminal、iTerm2、常见 Linux 终端）。

### 启动时提示"未找到 Profile"

`.vnag/profile/` 目录下需至少存在一个 Profile 配置文件，可通过图形界面创建，或手动创建 JSON 文件，格式参阅 [配置指南](../configuration/index.md#profile-配置)。

### `--task` 模式无输出

检查 `cli_setting.json` 中的网关配置是否正确，以及对应的 `connect_*.json` 是否填写了有效的 API Key。

## 下一步

- [CLI 使用教程](../tutorial/cli.md) - 从零开始的实操教程
- [配置指南](../configuration/index.md) - 完整的配置文件说明
- [图形界面](../ui/index.md) - 了解 GUI 模式的功能
