# vnag 多模态统一改造方案

## 1. 背景

当前 `vnag` 对多模态的支持处于“局部兼容”阶段：

- `Message.content` 已经允许 `str | list[dict[str, Any]]`
- 多数 Gateway 能在一定程度上消费用户侧多模态输入
- `TaskAgent`、`Response`、`Delta`、`UI` 仍然整体偏向“文本中心”
- assistant 侧非文本输出尚未形成统一的内部模型

这会带来几个长期问题：

1. 内部 canonical model 不稳定
2. `Message.content` 同时承担纯文本与弱类型 part list 两套语义
3. `Response` 与 `Delta` 的结构不统一
4. Gateway 里大量出现 provider-specific 的协议转换逻辑，但上层缺少稳定的中间抽象
5. 一旦需要支持图片等非文本输出，现有文本流式链路会迅速失衡

本文件给出一套以“概念统一”为目标的完整改造方案。

---

## 2. 设计目标

### 2.1 核心目标

将 `vnag` 的消息系统重构为：

- **正文统一**：所有用户/模型的正文内容都使用同一种结构表达
- **动作独立**：工具调用与工具结果继续作为独立的控制层数据
- **推理独立**：`thinking` / `reasoning` 继续独立，不并入正文
- **流式统一**：`Delta` 与 `Response` 尽可能表达同一类概念，只是一个是增量，一个是完成态
- **Provider 无关**：内部模型不直接使用某一家 API 的 wire format 作为 canonical model

### 2.2 非目标

本设计不追求：

- 完全复刻 Anthropic / OpenAI Responses / Gemini / Bedrock 中任意一家协议
- 让 `Message` 变成“所有 provider 原始 payload 的镜像”
- 一次性解决所有模态类型（先定义可扩展架构，再逐步接入）

---

## 3. 设计原则

### 3.1 正文与控制流分层

要区分三类信息：

1. **说了什么**：正文内容
2. **做了什么**：工具调用、工具结果
3. **怎么想的**：thinking、reasoning

其中：

- 正文属于 `content`
- 工具调用/结果不属于正文
- 推理信息也不属于正文

### 3.2 正文按顺序组织

多模态正文必须能够表达如下顺序：

1. 一段文本
2. 一张图片
3. 又一段文本
4. 再一张图片

因此，正文不能拆成：

- `content: str`
- `images: list[...]`
- `documents: list[...]`

而应该使用**按顺序排列的 parts**。

### 3.3 内部 canonical model 必须强类型

不建议长期停留在：

```python
list[dict[str, Any]]
```

原因：

- 弱类型
- 难做静态检查
- 容易把 provider 协议细节泄露到上层
- 难以演化

正确方向是：

- `Content`
- `Part`
- `TextPart`
- `ImagePart`
- 未来扩展更多 part

### 3.4 流式输出与完成态尽量同构

`Response` 和 `Delta` 不应是两套完全不相干的模型。

理想状态：

- `Response` 表示完整输出
- `Delta` 表示同一输出模型的增量

---

## 4. 推荐的目标对象模型

## 4.1 `Message`

建议长期演进为：

```python
class Message(BaseModel):
    role: Role
    content: Content = Field(default_factory=Content)
    thinking: str = ""
    reasoning: list[ReasoningItem] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
```

### 含义

- `content`：正文，多模态、强类型、按顺序组织
- `thinking`：供 UI 展示的思考文本
- `reasoning`：provider-specific 的结构化推理数据，用于跨轮回传和保真
- `tool_calls`：模型发起的动作请求
- `tool_results`：动作执行后的结构化观察结果
- `usage`：这条消息关联的 token 用量

### 为什么保留 `tool_calls / tool_results`

不建议把工具调用/结果塞进 `content`，原因如下：

1. 它们是编排层信号，不是正文
2. `TaskAgent` 当前控制流直接依赖 `tool_calls`
3. 不同 provider 对工具调用的编码方式差异极大
4. 内部保留独立字段，Gateway 更容易做协议翻译

---

## 4.2 `Content`

建议定义为：

```python
class Content(BaseModel):
    parts: list[Part] = Field(default_factory=list)
```

### 为什么不是裸 `list[Part]`

因为 `Content` 本身可以承载统一能力：

- `is_empty()`
- `to_plain_text()`
- `has_media()`
- `append_text()`
- `append_part()`
- `from_text()`

这些能力不适合分散在 UI、Agent、Gateway 中重复实现。

---

## 4.3 `Part`

推荐至少先定义两类：

```python
class TextPart(BaseModel):
    type: Literal["text"]
    text: str


class ImagePart(BaseModel):
    type: Literal["image"]
    mime_type: str
    data_base64: str | None = None
    uri: str | None = None
    name: str = ""


Part = TextPart | ImagePart
```

### 为什么 `ImagePart` 同时允许 `data_base64` 和 `uri`

因为图片来源可能有两类：

1. **内联内容**
   - 用户本地上传
   - 小图直接嵌入

2. **外部资源引用**
   - provider 返回图片 URL
   - 图像生成模型返回文件 URI
   - 工具生成本地文件并返回路径

如果只支持 `data_base64`，后续输出路径会很僵硬。

### 为什么内部不建议继续用 `image_url`

因为：

- `image_url` 更像 OpenAI-compatible 的 wire format
- 内部 canonical model 应该和 provider 解耦
- `mime_type + data_base64` / `uri` 的语义更清晰

---

## 4.4 `ToolCall`

保留独立模型：

```python
class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]
```

不建议并入 `Part`。

理由：

- 它不是正文
- 它触发 Agent Action 阶段
- 它更接近系统行为而不是内容块

---

## 4.5 `ToolResult`

建议长期保持独立：

```python
class ToolResult(BaseModel):
    id: str
    name: str
    content: str
    is_error: bool = False
```

未来如果确实需要“工具返回图片/文件”，可再扩展为：

```python
class ToolResult(BaseModel):
    id: str
    name: str
    content: str = ""
    parts: list[Part] = Field(default_factory=list)
    is_error: bool = False
```

但不建议第一阶段就做，因为这会显著扩大重构范围。

---

## 4.6 `ReasoningItem`

当前 `reasoning` 还是：

```python
list[dict[str, Any]]
```

长期建议也模型化，但优先级应低于 `content` 改造。

原因：

- `reasoning` 目前 provider-specific 差异很大
- 先把正文建模稳定，比先统一 reasoning 更有价值

建议阶段性策略：

1. 先保留 `list[dict[str, Any]]`
2. 在字段注释和使用边界上明确“只用于 provider 回传保真”
3. 待 `Content` 重构完成后，再评估是否引入 `ReasoningItem`

---

## 5. `Response` 与 `Delta` 的统一设计

## 5.1 设计目标

希望达到：

- `Response` 和 `Delta` 概念上更靠近
- 不引入 `MessageDelta`
- 保持流式文本处理路径高效
- 为未来非文本输出留出结构化空间

## 5.2 推荐方案

### `Response`

建议改为：

```python
class Response(BaseModel):
    id: str
    message: Message
    usage: Usage
    finish_reason: FinishReason | None = None
```

### 为什么删除 `Response.content`

当前 `Response.content` 和 `Response.message` 语义重复。

长期应该：

- `message` 作为唯一完整输出载体
- 需要便捷访问时，通过辅助属性获取纯文本

例如：

```python
@property
def text(self) -> str:
    return self.message.content.to_plain_text()
```

---

### `Delta`

不引入 `MessageDelta` 的前提下，推荐：

```python
class Delta(BaseModel):
    id: str
    text: str | None = None
    parts: list[Part] = Field(default_factory=list)
    thinking: str | None = None
    reasoning: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[ToolCall] | None = None
    finish_reason: FinishReason | None = None
    usage: Usage | None = None
    event: DeltaEvent | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
```

### 为什么保留 `text`

虽然理论上可以把文本增量也统一进 `parts`，但从工程实现角度不建议：

1. 文本是高频流式增量
2. 图片/文件通常是低频结构化块
3. 当前 UI/Agent 主链路天然适合字符串拼接
4. 保留 `text` 可以显著降低流式处理复杂度

### `parts` 的职责

- 非文本输出块
- 未来需要结构化追加的正文块
- 低频、完整、可插入的内容事件

### 为什么字段名建议用 `parts`

相比 `content_parts`：

- 更短
- 更自然
- 更接近 `Content.parts`
- 避免和 `Message.content` 出现冗余组合命名

---

## 6. 当前代码库的主要痛点与改造方向

## 6.1 `Message.content` 的弱 union

当前定义：

```python
content: str | list[dict[str, Any]] = ""
```

问题：

- 需要在大量代码里写 `isinstance`
- UI、Agent、Gateway 各自都在做一套降级逻辑
- 不利于长期扩展更多模态

方向：

- 改为 `Content`
- 通过统一方法处理文本提取与渲染视图

---

## 6.2 Agent 仍然是“文本响应中心”

当前 `TaskAgent` 内部：

- `StepResult.content` 是字符串
- `delta.content` 通过 `+=` 聚合
- `_request_text()` 直接拼文本

长期应改为：

```python
class StepResult:
    id: str = ""
    content: Content = field(default_factory=Content)
    thinking: str = ""
    reasoning: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    finish_reason: FinishReason | None = None
```

聚合策略：

- `delta.text` -> 追加到 `content.parts` 的文本部分
- `delta.parts` -> 直接 append

这样最终 assistant 消息就天然支持文本 + 图片等非文本输出。

---

## 6.3 UI 仍然是“纯文本流渲染”

当前 UI：

- `StreamWorker` 只发 `str`
- `HistoryWidget.append_message()` 对 assistant 只接受 `str`
- 历史重放与 Markdown 导出都偏文本化

长期改造方向：

1. worker 同时支持：
   - `text` 流
   - `parts` 事件
2. assistant UI 容器支持：
   - 连续追加文本
   - 中途插入图片/文件
3. Markdown 导出统一由 `Content` 决定降级策略

---

## 6.4 Gateway 仍在消费弱 union

当前多个 gateway 都在判断：

- `isinstance(msg.content, str)`
- `for part in msg.content`

长期应该统一为：

- Gateway 只接收 `Content`
- Gateway 负责把 `Content.parts` 翻译成 provider 协议

不要让 provider-specific 的表达反向污染上层。

---

## 7. Gateway 层的长期职责

## 7.1 总原则

Gateway 只做两件事：

1. **输入翻译**
   - `Message` -> provider request

2. **输出翻译**
   - provider response / stream -> `Response` / `Delta`

Gateway 不应该：

- 决定上层 canonical model 的形态
- 让 provider 的原始 payload 直接泄露到 UI / Agent / Session

---

## 7.2 输入翻译原则

### `Content.parts`

统一翻译成各家 API 的：

- text parts
- image blocks
- file/media inputs

### `tool_calls / tool_results`

继续独立翻译：

- Completion-compatible：独立 `tool_calls` / `tool` role 消息
- OpenAI Responses：`function_call` / `function_call_output`
- Anthropic：`tool_use` / `tool_result` blocks
- Bedrock：`toolUse` / `toolResult`
- Gemini：function call / function response parts
- Ollama：native tool message / tool call format

### `thinking / reasoning`

继续独立翻译，不混入正文。

---

## 7.3 输出翻译原则

文本输出：

- 放入 `Delta.text`
- 完整态进入 `Response.message.content`

非文本输出：

- 放入 `Delta.parts`
- 完整态进入 `Response.message.content.parts`

工具调用：

- 放入 `Delta.tool_calls`
- 完整态进入 `Response.message.tool_calls`

推理信息：

- 放入 `Delta.thinking` / `Delta.reasoning`
- 完整态进入 `Response.message.thinking` / `reasoning`

---

## 8. Session 持久化与兼容策略

## 8.1 风险

当前 session 是直接 `model_dump()` 存盘。

如果 `Message.content` 改造，历史 session 会受影响。

### 风险点

1. 旧 session 中 `content` 可能是字符串
2. 新 session 中 `content` 变成结构化对象
3. 需要兼容历史加载

## 8.2 推荐兼容策略

### 阶段一：兼容读取

新 `Content` 模型在解析时支持：

- 旧字符串
- 旧 `list[dict]`
- 新 `Content`

并统一转成内部 `Content`

### 阶段二：新格式写盘

新版本写出的 session 一律使用新结构。

### 阶段三：移除旧兼容

待版本稳定、用户历史迁移充分后，再考虑移除旧格式入口。

---

## 9. 推荐迁移步骤

## 阶段 1：定义新对象模型

目标文件：

- `vnag/object.py`

工作：

- 引入 `Content`
- 引入 `Part`、`TextPart`、`ImagePart`
- 调整 `Message`
- 调整 `Response`
- 调整 `Delta`

产物：

- 新 canonical model 成立
- 暂不大规模改业务逻辑

---

## 阶段 2：给 `Content` 增加统一能力

建议提供：

- `from_text(text: str) -> Content`
- `to_plain_text() -> str`
- `is_empty() -> bool`
- `has_media() -> bool`
- `append_text(text: str) -> None`
- `append_part(part: Part) -> None`

这样后续 Agent/UI/Gateway 的迁移成本会显著下降。

---

## 阶段 3：改 Agent

目标：

- 把 `StepResult.content` 从字符串改为 `Content`
- 把 `delta.text / delta.parts` 聚合回 `Content`
- 把摘要、标题、轮次、压缩等逻辑统一走 `to_plain_text()`

重点文件：

- `vnag/agent.py`

---

## 阶段 4：改 UI

目标：

- 用户侧输入构建 `Content`
- assistant 流式支持：
  - 文本连续追加
  - 图片/文件插入
- 历史重放基于 `Content`
- Markdown 导出基于 `Content`

重点文件：

- `vnag/ui/worker.py`
- `vnag/ui/widget.py`

---

## 阶段 5：改 Gateway

目标：

- 不再依赖 `str | list[dict]`
- 全部消费 `Content`
- 输出统一产出 `Delta.text` / `Delta.parts`

重点文件：

- `vnag/gateways/completion_gateway.py`
- `vnag/gateways/openai_gateway.py`
- `vnag/gateways/anthropic_gateway.py`
- `vnag/gateways/gemini_gateway.py`
- `vnag/gateways/bedrock_gateway.py`
- `vnag/gateways/ollama_gateway.py`
- 其他兼容型网关

---

## 阶段 6：测试与文档

新增测试类别：

1. `Content` 模型单测
2. 文本与图片输入的 Gateway 转换单测
3. assistant 非文本输出的 `Delta.parts` / `Response.message.content` 单测
4. session 新旧格式兼容测试
5. UI 历史重放与 Markdown 导出测试

文档需要同步更新：

- `object.py` 数据结构说明
- Gateway 开发文档
- 多模态支持文档
- Session 兼容说明

---

## 10. 推荐的最终设计结论

## 10.1 正文层

采用：

- `Message.content: Content`
- `Content.parts: list[Part]`

而不是：

- `str | list[dict]`
- `content: str + images: list[...]`

## 10.2 动作层

保留：

- `tool_calls`
- `tool_results`

继续独立，不并入正文。

## 10.3 推理层

保留：

- `thinking`
- `reasoning`

继续独立，不并入正文。

## 10.4 响应层

采用：

- `Response.message`
- `Delta.text`
- `Delta.parts`

不引入 `MessageDelta`，但保持 `Response` / `Delta` 在概念上尽量一致。

---

## 11. 最终推荐的一句话

`vnag` 的长期多模态统一方案，应当是：

**让 `content` 成为强类型、按顺序组织的正文容器；让 `tool_calls / tool_results / reasoning` 继续作为独立的控制与元信息层；让 `Response` 和 `Delta` 围绕同一个正文模型收敛，而不是继续围绕纯文本拼接发展。**

