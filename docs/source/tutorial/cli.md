# 使用命令行界面

本教程将带您从零开始使用 VNAG 的 CLI 模式，包括配置、启动、对话和常用命令。

**预计时间**：10 分钟  
**难度**：⭐

## 前置要求

- 完成 [安装指南](../getting_started/installation.md)
- 至少配置了一个网关的 API Key（参阅 [配置指南](../configuration/index.md#网关配置)）
- 通过图形界面或手动创建了至少一个 Profile

## 第一步：创建 CLI 配置

在您的工作目录下的 `.vnag/` 文件夹中创建 `cli_setting.json`：

```json
{
    "gateway_name": "OpenAI",
    "profile_name": "助手",
    "model_name": "gpt-4o-mini"
}
```

将 `gateway_name` 替换为您实际使用的网关类型，`profile_name` 替换为您已有的 Profile 名称。

:::{note}
如果 `profile_name` 填写的 Profile 不存在，CLI 会自动使用第一个可用的 Profile，不会报错退出。
:::

## 第二步：启动交互模式

```bash
python -m vnag.cli
```

启动成功后，终端会显示欢迎信息和输入提示符：

```
  ✻ VeighNa Agent
  Profile: 助手
  Model:   gpt-4o-mini
  Session: 20240115_103000_123456
  输入 /help 查看命令

You › 
```

底部状态栏实时显示当前 Profile、模型和消息数。

## 第三步：进行对话

在 `You › ` 后输入问题，按 `Enter` 发送：

```
You › 你好，请介绍一下你自己
```

AI 会以流式方式逐字输出回答，工具调用过程也会实时显示：

```
你好！我是基于 VeighNa Agent 框架构建的 AI 助手……

──────────────────────────────────────────
You › 
```

**按 `Ctrl+C` 可随时中止当前生成。**

## 第四步：使用 Tab 补全

CLI 支持两种自动补全，按 `Tab` 键触发：

**斜杠命令补全**：输入 `/` 后按 `Tab`，列出所有命令：

```
You › /
/help     /clear    /model    /profile
/retry    /sessions /title    /stats    /exit
```

**文件路径补全**：输入 `@` 后按 `Tab`，浏览文件：

```
You › 请分析 @src/
src/main.py    src/utils.py    src/config/
```

## 第五步：使用斜杠命令

### 切换模型

```
You › /model gpt-4o
模型已切换为: gpt-4o
```

切换后立即生效，并持久化保存到 `cli_setting.json`。

### 切换 Profile

```
You › /profile 代码专家
已切换到 Profile: 代码专家
```

切换 Profile 会创建新会话。

### 查看会话统计

```
You › /stats
  消息数: 6  |  Session: 20240115_103000_123456
```

### 列出所有会话

```
You › /sessions
  → 20240115_103000_123456  我的问题
    20240114_090000_654321  代码审查
```

`→` 标记当前活动会话。

### 自动生成标题

```
You › /title
标题已更新: Python 列表推导式用法
```

CLI 会调用 AI 根据对话内容自动为会话命名。

### 重发上一轮

```
You › /retry
```

弹出并重新提交最近一条用户输入，便于修改提问后再次发送。

## 第六步：使用非交互模式

非交互模式适合脚本集成，执行单次任务后自动退出：

```bash
python -m vnag.cli --task "用 Python 写一个冒泡排序函数"
```

**与其他命令组合使用**：

```bash
# 将 AI 输出保存到文件
python -m vnag.cli --task "总结以下代码：$(cat main.py)" > summary.txt

# 在 Shell 脚本中使用
RESULT=$(python -m vnag.cli --task "判断这段日志是否有错误：$(cat app.log)")
echo "$RESULT"
```

## 退出 CLI

有以下三种方式退出：

- 输入 `/exit`
- 按 `Ctrl+D`（发送 EOF）
- 按 `Ctrl+C`（在非生成状态下）

```
You › /exit

再见。
```

## 下一步

- [命令行界面文档](../cli/index.md) - 完整功能参考
- [使用图形界面](chat_ui.md) - 了解 GUI 模式
- [配置指南](../configuration/index.md) - 配置文件详细说明
