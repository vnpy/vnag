import json
from dataclasses import dataclass, field
from pathlib import Path
import profile
from uuid import uuid4
from typing import TYPE_CHECKING, Any
from collections.abc import Generator

from .object import (
    Session, Profile, Delta, Request, Response, Message,
    Usage, ToolCall, ToolResult, ToolSchema
)
from .constant import Role, FinishReason, DeltaEvent
from .utility import SESSION_DIR
from .tracer import LogTracer

if TYPE_CHECKING:
    from .engine import AgentEngine


@dataclass
class StepResult:
    """单次 LLM 调用的收集结果（ReAct 循环中的一个 step）"""
    id: str = ""
    content: str = ""
    thinking: str = ""
    reasoning: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    finish_reason: FinishReason | None = None


# 构建总结请求的提示词
TITLE_PROMPT: str = """
请根据以上对话内容，生成一个简洁的标题来概括这次会话的主题。

要求：
1. 标题应该准确反映对话的核心内容和主要议题
2. 标题长度不超过{max_length}个字
3. 使用简洁、专业、易懂的语言
4. 直接返回标题文本，不需要引号、标点或额外说明
5. 如果对话涉及多个话题，提取最主要的主题
"""

COMPACTION_MAX_TOKENS: int = 1024
COMPACTION_PROMPT: str = f"""
请将以上对话压缩为一段供后续继续对话使用的上下文摘要。

要求：
1. 保留用户目标、已确认事实、重要结论、未完成事项和关键约束。
2. 记录重要的文件名、工具结果结论、术语或实体名称。
3. 忽略寒暄、重复表达和冗长工具输出细节。
4. 使用简洁、连续的中文表述，直接返回摘要正文，不要附加说明。
5. 必须在不超过{COMPACTION_MAX_TOKENS}个 token 的输出预算内完整写完摘要，不要输出半句或未完成列表。
"""

SUMMARY_PREFIX: str = "[vnag:session_summary]"


class TaskAgent:
    """
    标准的、可直接使用的任务智能体。
    """

    def __init__(
        self,
        engine: "AgentEngine",
        profile: Profile,
        session: Session,
        save: bool = False
    ) -> None:
        """构造函数"""
        self.engine: AgentEngine = engine
        self.profile: Profile = profile
        self.session: Session = session
        self.save: bool = save

        self.tracer: LogTracer = LogTracer(
            session_id=self.session.id,
            profile_name=self.profile.name
        )

        # 当前 step 的收集结果（中止时可通过此恢复部分内容）
        self.current_step: StepResult | None = None

        # 中止标志
        self.aborted: bool = False

        # 最后一轮对话状态：用户 prompt 和轮次起始索引
        self.round_prompt: str = ""
        self.round_start: int = 0

        # 确保会话始终以 system 消息开头，后续逻辑都依赖这个约定。
        self._ensure_system_message()

        # 更新摘要偏移量
        self._normalize_offset()

        # 从已有消息推导最后一轮状态
        self._init_round()

    def _init_round(self) -> None:
        """从已有消息推导最后一轮的轮次状态"""
        for i in range(len(self.session.messages) - 1, -1, -1):
            msg: Message = self.session.messages[i]
            if msg.role == Role.SYSTEM:
                break
            if msg.role == Role.USER and msg.content:
                self.round_prompt = msg.content
                self.round_start = i
                return

        self.round_prompt = ""
        self.round_start = len(self.session.messages)

    def _ensure_system_message(self) -> None:
        """确保会话首条消息始终为 system"""
        if self.session.messages and self.session.messages[0].role == Role.SYSTEM:
            return

        system_content: str = self.profile.prompt

        # 如果启用了技能，追加 Level 1 技能目录
        if self.profile.use_skills:
            skill_catalog: str = self.engine.get_skill_catalog()
            if skill_catalog:
                system_content += "\n\n" + skill_catalog

        system_message: Message = Message(
            role=Role.SYSTEM,
            content=system_content
        )

        if self.session.messages:
            self.session.messages.insert(0, system_message)
        else:
            self.session.messages.append(system_message)

        self._save_session()

    def _normalize_offset(self) -> None:
        """规范化摘要偏移量，避免请求窗口越界"""
        # 会话首条始终为 system，因此 offset 至少应跳过它
        min_offset: int = 1

        # 没有摘要时，不需要跳过任何普通消息，直接回到首条普通消息边界
        if not self.session.summary:
            self.session.offset = min_offset
            return

        # 已有摘要时，offset 不能小于最小边界，也不能超过当前消息列表长度
        self.session.offset = min(
            max(self.session.offset, min_offset),
            len(self.session.messages),
        )

    def _save_session(self) -> None:
        """保存会话状态到文件"""
        if not self.save:
            return

        data: dict = self.session.model_dump()
        file_path: Path = SESSION_DIR.joinpath(f"{self.session.id}.json")

        with open(file_path, mode="w+", encoding="UTF-8") as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

    def _merge_reasoning(
        self,
        collected: list[dict[str, Any]],
        incoming: list[dict[str, Any]],
    ) -> None:
        """将增量 reasoning 数据合并到已收集列表中（按 index 拼接字符串字段）"""
        for new_item in incoming:
            # 如果没有 index，直接追加
            if "index" not in new_item:
                collected.append(new_item)
                continue

            # 查找是否存在相同 index 的项
            existing_item = next(
                (item for item in collected
                 if item.get("index") == new_item["index"]),
                None
            )

            if existing_item:
                # 合并字段
                for key, value in new_item.items():
                    # 字符串类型的字段进行拼接（signature 不拼接）
                    if key in ["text", "data", "summary"] and isinstance(value, str):
                        existing_item[key] = existing_item.get(key, "") + value
                    # 其他字段直接覆盖（如 type, format, id, signature 等）
                    else:
                        existing_item[key] = value
            else:
                # 不存在则追加
                collected.append(new_item)

    def _get_last_input_tokens(self) -> int:
        """返回最近一次模型请求的输入 token 数。"""
        for message in reversed(self.session.messages):
            if message.role == Role.ASSISTANT:
                return message.usage.input_tokens

        return 0

    def _get_request_messages(self) -> list[Message]:
        """构造发送给模型的请求消息"""
        messages: list[Message] = list(self.session.messages)

        if not self.session.summary:
            return messages

        self._normalize_offset()

        summary_message: Message = Message(
            role=Role.USER,
            content=f"{SUMMARY_PREFIX}\n{self.session.summary}",
        )

        return [messages[0], summary_message, *messages[self.session.offset:]]

    def _get_compaction_target(self) -> tuple[list[Message], int] | None:
        """返回可压缩的旧消息及保留区间起点"""
        self._normalize_offset()

        keep_turns: int = max(1, self.profile.compaction_turns)
        user_turns: int = 0
        preserve_start: int | None = None

        # 从后向前遍历消息列表，找到保留区间的起点
        for index in range(len(self.session.messages) - 1, 0, -1):
            message: Message = self.session.messages[index]

            # 以用户消息为分界点，计算保留区间的长度
            if message.role == Role.USER and message.content:
                user_turns += 1
                if user_turns >= keep_turns:
                    preserve_start = index
                    break

        if preserve_start is None or preserve_start <= self.session.offset:
            return None

        messages_to_compact: list[Message] = self.session.messages[
            self.session.offset:preserve_start
        ]
        if not messages_to_compact:
            return None

        return messages_to_compact, preserve_start

    def _request_text(self, request: Request) -> str:
        """聚合流式响应中的纯文本内容"""
        full_content: str = ""

        for delta in self.engine.stream(request):
            if delta.content:
                full_content += delta.content

        return full_content.strip()

    def _generate_summary(self, messages_to_compact: list[Message]) -> str:
        """为待压缩的旧消息生成滚动摘要"""
        summary_messages: list[Message] = [self.session.messages[0]]

        if self.session.summary:
            summary_messages.append(
                Message(
                    role=Role.USER,
                    content=(
                        f"{SUMMARY_PREFIX}\n"
                        f"{self.session.summary}"
                    ),
                )
            )

        summary_messages.extend(messages_to_compact)
        summary_messages.append(Message(role=Role.USER, content=COMPACTION_PROMPT))

        request: Request = Request(
            model=self.session.model,
            messages=summary_messages,
            tool_schemas=[],
            temperature=1.0,
            max_tokens=self.profile.max_tokens,
        )

        summary: str = self._request_text(request)
        return summary

    def _maybe_compact_session(self) -> None:
        """在请求发送前按需压缩旧消息"""
        threshold: int = self.profile.compaction_threshold
        if threshold <= 0:
            return

        last_input_tokens: int = self._get_last_input_tokens()
        if last_input_tokens <= threshold:
            return

        compaction_target = self._get_compaction_target()
        if not compaction_target:
            return

        messages_to_compact, preserve_start = compaction_target

        try:
            summary: str = self._generate_summary(messages_to_compact)
        except Exception:
            return

        if not summary:
            return

        self.session.summary = summary
        self.session.offset = preserve_start

        self._save_session()

    def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """执行单个工具调用（含异常隔离）"""
        try:
            return self.engine.execute_tool(tool_call)
        except Exception as e:
            return ToolResult(
                id=tool_call.id,
                name=tool_call.name,
                content=f"工具执行失败: {type(e).__name__}: {e}",
                is_error=True,
            )

    def _get_tool_schemas(self) -> list[ToolSchema]:
        """
        查询当前 profile 的工具 Schema 列表（含 skill 工具）

        根据 profile.tools 中声明的工具名称列表，从引擎获取对应的
        ToolSchema 定义；若 profile.use_skills 为 True，还会额外
        追加 skill（技能）工具的 Schema，供 LLM 决策调用。
        """
        # 获取 profile 中声明的基础工具 Schema
        schemas: list[ToolSchema] = self.engine.get_tool_schemas(self.profile.tools)

        # 如果启用了 skill，追加 skill 工具 Schema
        if self.profile.use_skills:
            skill_schema: ToolSchema | None = self.engine.get_skill_schema()
            if skill_schema:
                schemas.append(skill_schema)

        return schemas

    def _finalize_stream(self, checkpoint: int) -> None:
        """
        流式结束后的清理：回滚不完整消息、保存会话

        当流式过程被中止（self.aborted=True）时，checkpoint 之后追加的
        消息（包含不完整的工具调用/结果）会被回滚删除；但如果 LLM 已产出
        了部分文本/思考内容，则保留为一条不完整的 assistant 消息，避免
        用户侧丢失已展示的内容。最终无论是否中止都会持久化会话。
        """
        if self.aborted and len(self.session.messages) > checkpoint:
            # 回滚 checkpoint 之后的所有消息（不完整的工具调用/结果）
            del self.session.messages[checkpoint:]

            # 如果已收集到部分内容，保留为不完整的 assistant 消息
            step: StepResult | None = self.current_step
            if step and (step.content or step.thinking):
                partial_msg = Message(
                    role=Role.ASSISTANT,
                    content=step.content,
                    thinking=step.thinking,
                    reasoning=step.reasoning,
                    usage=step.usage,
                )
                self.session.messages.append(partial_msg)

        self.current_step = None
        self._save_session()

    @property
    def id(self) -> str:
        """任务ID"""
        return self.session.id

    @property
    def name(self) -> str:
        """任务名称"""
        return self.session.name

    @property
    def model(self) -> str:
        """模型名称"""
        return self.session.model

    @property
    def messages(self) -> list[Message]:
        """会话消息"""
        return self.session.messages

    def stream(self, prompt: str) -> Generator[Delta, None, None]:
        """
        流式生成（ReAct 编排器）

        实现 ReAct（Reasoning + Acting）循环：
        1. Thought  — 调用 LLM，流式收集响应（content / thinking / tool_calls）
        2. Action   — 若 LLM 请求工具调用，逐一执行并通过事件通知前端
        3. Observation — 将工具结果注入会话上下文，回到 step 1

        循环在以下任一条件满足时退出：
        - LLM 返回 finish_reason=STOP（正常结束）
        - 达到 max_iterations 上限（发出 WARNING 事件）
        - 外部调用 abort()（中止）
        - 发生异常（标记中止后重新抛出）

        所有 Delta 均通过 yield 向上层（UI / Worker）传递，
        stream() 是唯一的 yield 源，不使用子生成器。
        """
        # 重置中止标志
        self.aborted = False

        # 记录轮次起点（用于 UI 层定位本轮消息范围）
        self.round_prompt = prompt
        self.round_start = len(self.session.messages)

        # 将用户输入添加到会话
        user_message: Message = Message(
            role=Role.USER,
            content=prompt
        )
        self.session.messages.append(user_message)

        # 初始化变量
        iteration: int = 0                                  # 当前迭代次数
        response_id: str = ""                               # 首次 LLM 响应 ID，用于后续事件关联
        checkpoint: int = len(self.session.messages)        # 消息回滚点（中止时回滚到此位置）

        # 查询工具定义（profile 声明的工具 + skill 工具）
        tool_schemas: list[ToolSchema] = self._get_tool_schemas()

        # ReAct 主循环，每次迭代包含一次完整的 Thought → Action → Observation
        # 当 LLM 不再请求工具调用时退出循环
        try:
            while iteration < self.profile.max_iterations:
                # 检查中止标志
                if self.aborted:
                    break

                iteration += 1

                # 在发送请求前按需压缩旧消息
                self._maybe_compact_session()

                # 更新回滚点
                checkpoint = len(self.session.messages)

                request_messages: list[Message] = self._get_request_messages()

                # 构造 LLM 请求
                request: Request = Request(
                    model=self.session.model,
                    messages=request_messages,
                    tool_schemas=tool_schemas,
                    temperature=self.profile.temperature,
                    max_tokens=self.profile.max_tokens
                )

                # 调用追踪器：记录请求发送
                self.tracer.on_llm_start(request)

                # Thought: 流式收集 LLM 响应，并实时 yield 给上层消费
                step: StepResult = StepResult()
                self.current_step = step

                for delta in self.engine.stream(request):
                    # 拼接 ID
                    if delta.id and not step.id:
                        step.id = delta.id

                    # 拼接内容
                    if delta.content:
                        step.content += delta.content

                    # 拼接思考
                    if delta.thinking:
                        step.thinking += delta.thinking

                    # 合并底层推理信息
                    if delta.reasoning:
                        self._merge_reasoning(step.reasoning, delta.reasoning)

                    # 拼接工具调用
                    if delta.tool_calls:
                        step.tool_calls.extend(delta.tool_calls)

                    # 累加 Token 使用量
                    if delta.usage:
                        step.usage.input_tokens += delta.usage.input_tokens
                        step.usage.output_tokens += delta.usage.output_tokens

                    # 拼接结束原因
                    if delta.finish_reason:
                        step.finish_reason = delta.finish_reason

                    # 调用追踪器：记录 delta 接收
                    self.tracer.on_llm_delta(delta)

                    yield delta

                # 记录首次响应 ID，后续工具事件复用此 ID
                if not response_id and step.id:
                    response_id = step.id

                # 将完整的 AI 回复追加到会话历史
                assistant_msg: Message = Message(
                    role=Role.ASSISTANT,
                    content=step.content,
                    thinking=step.thinking,
                    reasoning=step.reasoning,
                    tool_calls=step.tool_calls,
                    usage=step.usage,
                )
                self.session.messages.append(assistant_msg)

                # 调用追踪器：记录响应接收
                self.tracer.on_llm_end(assistant_msg)

                # Action: 优先依据"事实上存在的工具调用"驱动控制流。
                # 不以 finish_reason 作为是否执行工具的唯一依据，
                # 避免 OpenAI 兼容网关将工具调用轮误标为 "stop" 时 Agent 提前终止。
                if step.tool_calls:
                    rid: str = response_id or str(uuid4())
                    tool_results: list[ToolResult] = []

                    for tool_call in step.tool_calls:
                        if self.aborted:
                            break

                        # 通知前端：工具开始执行
                        yield Delta(
                            id=rid,
                            event=DeltaEvent.TOOL_START,
                            payload={"name": tool_call.name}
                        )
                        self.tracer.on_tool_start(tool_call)

                        # 执行工具（异常已在 _execute_tool 中隔离）
                        tool_result: ToolResult = self._execute_tool(tool_call)
                        tool_results.append(tool_result)

                        # 通知前端：工具执行完成
                        yield Delta(
                            id=rid,
                            event=DeltaEvent.TOOL_END,
                            payload={
                                "name": tool_call.name,
                                "success": not tool_result.is_error,
                            },
                        )
                        self.tracer.on_tool_end(tool_result)

                    # 中止时不添加不完整的工具结果
                    if self.aborted:
                        break

                    # Observation: 将工具结果注入会话
                    self.session.messages.append(
                        Message(role=Role.USER, tool_results=tool_results)
                    )

                    # 继续下一次 ReAct 迭代
                    continue

                # 正常结束（LLM 不再需要工具），退出循环
                if step.finish_reason == FinishReason.STOP:
                    break

                # 输出被 token 长度限制截断
                if step.finish_reason == FinishReason.LENGTH:
                    yield Delta(
                        id=response_id or str(uuid4()),
                        event=DeltaEvent.WARNING,
                        payload={"message": "模型输出因长度限制被截断"},
                    )
                    break

                # 其他非预期结束原因（unknown / error / None）
                if step.finish_reason in {
                    FinishReason.UNKNOWN, FinishReason.ERROR, None
                }:
                    yield Delta(
                        id=response_id or str(uuid4()),
                        event=DeltaEvent.WARNING,
                        payload={"message": "模型以非预期结束原因结束"},
                    )
                    break

                break

            # 仅当循环因达到迭代上限而退出（非正常 STOP / break）时才发出警告
            if not self.aborted and iteration >= self.profile.max_iterations:
                yield Delta(
                    id=response_id or str(uuid4()),
                    event=DeltaEvent.WARNING,
                    payload={"message": "达到最大迭代次数限制"},
                )

        except Exception:
            # 异常时标记中止，确保 finally 中统一清理
            self.aborted = True
            raise
        finally:
            # 无论正常结束还是异常/中止，都执行清理和会话持久化
            self._finalize_stream(checkpoint)

    def abort_stream(self) -> None:
        """中止流式生成"""
        self.aborted = True

    def invoke(self, prompt: str) -> Response:
        """阻塞式生成"""
        full_content: str = ""
        response_id: str = ""
        total_usage: Usage = Usage()

        # 遍历 stream 方法返回的生成器，消费所有 Delta 数据
        for delta in self.stream(prompt):
            if delta.id:
                response_id = delta.id

            # 拼接完整的文本内容
            if delta.content:
                full_content += delta.content

            # 累加 Token 使用量
            if delta.usage:
                total_usage.input_tokens += delta.usage.input_tokens
                total_usage.output_tokens += delta.usage.output_tokens

        # 将所有收集到的信息组装成一个 Response 对象并返回
        return Response(
            id=response_id,
            content=full_content,
            usage=total_usage
        )

    def rename(self, name: str) -> None:
        """重命名任务"""
        self.session.name = name

        self._save_session()

    def delete_round(self) -> None:
        """删除最后一轮对话，截断到轮次起始位置"""
        if not self.round_prompt:
            return

        del self.session.messages[self.round_start:]
        self._normalize_offset()
        self._init_round()
        self._save_session()

    def pop_round(self) -> str:
        """删除最后一轮对话并返回用户 prompt（用于重发）"""
        prompt: str = self.round_prompt
        self.delete_round()
        return prompt

    def set_model(self, model: str) -> None:
        """设置模型"""
        self.session.model = model

        self._save_session()

    def generate_title(self, max_length: int = 20) -> str:
        """生成会话标题"""
        # 复制会话消息并添加总结请求
        messages: list[Message] = self._get_request_messages()
        messages.append(Message(role=Role.USER, content=TITLE_PROMPT.format(max_length=max_length)))

        # 构造请求（固定温度，避免上游 API 拒绝 null temperature）
        request: Request = Request(
            model=self.session.model,
            messages=messages,
            tool_schemas=[],
            temperature=1.0,
            max_tokens=self.profile.max_tokens
        )

        # 调用 LLM 生成标题
        full_content: str = self._request_text(request)

        # 返回生成的标题（去除首尾空白和可能的引号）
        title: str = full_content.strip()

        # 移除可能的引号
        for quote in ['"', "'", '"', '"', ''', ''']:
            if title.startswith(quote) and title.endswith(quote):
                title = title[1:-1]
                break

        return title


class AgentTool:
    """
    智能体工具：将 Profile 封装为可调用的工具。

    每次调用时创建新的 TaskAgent 实例，不保留对话历史。
    """

    def __init__(
        self,
        engine: "AgentEngine",
        profile: Profile,
        model: str,
        name: str = "",
        description: str = "",
    ) -> None:
        """构造函数"""
        if not name:
            name = profile.name

        if not description:
            description = f"调用智能体 [{profile.name}] 处理任务"

        # 使用"-"替换"_"，和其他工具保持一致
        name = name.replace("_", "-")
        self.name: str = f"agent_{name}"

        self.description: str = description
        self.engine: AgentEngine = engine
        self.profile: Profile = profile
        self.model: str = model

        self.parameters: dict[str, Any] = {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "发送给智能体的提示词"
                }
            },
            "required": ["prompt"]
        }

    def get_schema(self) -> ToolSchema:
        """获取工具的 Schema"""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self.parameters
        )

    def execute(self, prompt: str) -> str:
        """执行工具"""
        # 创建新的 TaskAgent 实例
        agent: TaskAgent = self.engine.create_agent(
            self.profile,
            save=False      # 不保存会话，因为每次调用都是新的会话
        )

        # 设置模型
        agent.set_model(self.model)

        # 使用invoke方法执行任务
        response: Response = agent.invoke(prompt)

        # 返回AI模型的回复内容
        return response.content
