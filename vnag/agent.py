import json
from pathlib import Path
from uuid import uuid4
from typing import TYPE_CHECKING
from collections.abc import Generator

from .object import (
    Session, Profile, Delta, Request, Response, Message,
    Usage, ToolCall, ToolResult, ToolSchema
)
from .constant import Role, FinishReason
from .utility import SESSION_DIR
from .tracer import LogTracer

if TYPE_CHECKING:
    from .engine import AgentEngine


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


class TaskAgent:
    """
    标准的、可直接使用的任务智能体。
    """

    def __init__(self, engine: "AgentEngine", profile: Profile, session: Session):
        """构造函数"""
        self.engine: AgentEngine = engine
        self.profile: Profile = profile
        self.session: Session = session

        self.tracer: LogTracer = LogTracer(
            session_id=self.session.id,
            profile_name=self.profile.name
        )

        # 流式生成时累积的内容
        self.collected_content: str = ""
        self.collected_tool_calls: list[ToolCall] = []

        # 新会话自动添加系统提示词并保存
        if not self.session.messages:
            system_message: Message = Message(
                role=Role.SYSTEM,
                content=self.profile.prompt
            )
            self.session.messages.append(system_message)

            self._save_session()

    def _save_session(self) -> None:
        """保存会话状态到文件"""
        data: dict = self.session.model_dump()
        file_path: Path = SESSION_DIR.joinpath(f"{self.session.id}.json")

        with open(file_path, mode="w+", encoding="UTF-8") as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

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
        """流式生成"""
        # 将用户输入添加到会话
        user_message: Message = Message(
            role=Role.USER,
            content=prompt
        )
        self.session.messages.append(user_message)

        # 初始化变量
        iteration: int = 0                                  # 迭代次数
        response_id: str = ""                               # 响应ID

        # 查询工具定义
        tool_schemas: list[ToolSchema] = self.engine.get_tool_schemas(self.profile.tools)

        # 主循环，该循环负责处理多次工具调用的情况
        while iteration < self.profile.max_iterations:
            # 重置收集的内容
            self.collected_content = ""
            self.collected_tool_calls = []

            # 迭代次数加1
            iteration += 1

            # 准备请求
            request: Request = Request(
                model=self.session.model,
                messages=self.session.messages,
                tool_schemas=tool_schemas,
                temperature=self.profile.temperature,
                max_tokens=self.profile.max_tokens
            )

            # 调用追踪器：记录请求发送
            self.tracer.on_llm_start(request)

            # 本轮循环中的数据缓存
            finish_reason: FinishReason | None = None       # 累积收到的结束原因

            # 发送请求到AI服务端，并收集响应
            for delta in self.engine.stream(request):
                # 记录响应ID
                if delta.id and not response_id:
                    response_id = delta.id

                # 累积收到的文本内容
                if delta.content:
                    self.collected_content += delta.content

                # 累积收到的工具调用请求
                if delta.calls:
                    self.collected_tool_calls.extend(delta.calls)

                # 记录结束原因
                if delta.finish_reason:
                    finish_reason = delta.finish_reason

                # 调用追踪器：记录收到数据块
                self.tracer.on_llm_delta(delta)

                # 将原始的 Delta 对象直接转发给调用者，实现实时流式效果
                yield delta

            # 将AI的回复（包括思考过程和工具调用请求）作为一个消息添加到会话中
            assistant_msg: Message = Message(
                role=Role.ASSISTANT,
                content=self.collected_content,
                tool_calls=self.collected_tool_calls
            )

            self.session.messages.append(assistant_msg)

            # 调用追踪器：记录响应接收
            self.tracer.on_llm_end(assistant_msg)

            # 正常结束则直接退出循环
            if finish_reason == FinishReason.STOP:
                break
            # 模型要求调用工具
            elif (
                finish_reason == FinishReason.TOOL_CALLS
                and self.collected_tool_calls    # 且收到了具体的工具调用请求
            ):
                # 批量执行所有工具调用
                tool_results: list[ToolResult] = []

                for tool_call in self.collected_tool_calls:
                    # 在执行前，先通过 yield 发送一个通知，告诉上层应用"正在执行哪个工具"
                    yield Delta(
                        id=response_id or str(uuid4()),
                        content=f"\n\n[执行工具: {tool_call.name}]\n\n"
                    )

                    # 调用追踪器：记录工具开始执行
                    self.tracer.on_tool_start(tool_call)

                    # 执行单个工具调用，并记录结果
                    result: ToolResult = self.engine.execute_tool(tool_call)
                    tool_results.append(result)

                    # 调用追踪器：记录工具执行完毕
                    self.tracer.on_tool_end(result)

                # 将所有工具的执行结果打包成一个消息，也添加到工作列表中
                user_message = Message(
                    role=Role.USER,
                    tool_results=tool_results
                )
                self.session.messages.append(user_message)

                # 继续下一次循环
                continue
            # 其他异常情况，直接退出
            else:
                break

        # 如果循环次数达到上限，发送一条警告信息
        if iteration >= self.profile.max_iterations:
            yield Delta(
                id=response_id or str(uuid4()),
                content="\n[警告: 达到最大工具调用次数限制]\n"
            )

        # 将最新会话保存到文件
        self._save_session()

    def abort_stream(self) -> None:
        """中止流式生成，保存已生成的部分内容"""
        # 检查是否有内容需要保存
        if not self.collected_content:
            return

        # 保存部分生成的内容
        assistant_msg = Message(
            role=Role.ASSISTANT,
            content=self.collected_content,
            tool_calls=self.collected_tool_calls
        )
        self.session.messages.append(assistant_msg)

        self._save_session()

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
        """删除最后一轮对话"""
        # 必须有对话历史，且最后一条是助手消息
        if (
            not self.messages
            or self.messages[-1].role != Role.ASSISTANT
        ):
            return

        # 删除最后一轮对话（用户消息和助手消息）
        self.messages.pop()
        self.messages.pop()

        # 保存会话状态
        self._save_session()

    def resend_round(self) -> str:
        """重新发送最后一轮对话"""
        # 必须有对话历史，且最后一条是助手消息
        if (
            not self.messages
            or self.messages[-1].role != Role.ASSISTANT
        ):
            return ""

        # 删除助手消息
        self.messages.pop()

        # 删除用户消息
        user_message: Message = self.messages.pop()

        # 保存会话状态
        self._save_session()

        # 返回用户消息内容
        return user_message.content

    def set_model(self, model: str) -> None:
        """设置模型"""
        self.session.model = model

        self._save_session()

    def generate_title(self, max_length: int = 20) -> str:
        """生成会话标题"""
        # 复制会话消息并添加总结请求
        messages: list[Message] = self.session.messages.copy()
        messages.append(Message(role=Role.USER, content=TITLE_PROMPT.format(max_length=max_length)))

        # 构造请求（使用较低温度以获得更稳定的结果）
        request: Request = Request(
            model=self.session.model,
            messages=messages,
            tool_schemas=[],
            temperature=0.5,
            max_tokens=max(max_length * 3, 50)  # 设置为 max_length 的 3 倍，留出足够的余量
        )

        # 调用 LLM 生成标题
        full_content: str = ""
        for delta in self.engine.stream(request):
            if delta.content:
                full_content += delta.content

        # 返回生成的标题（去除首尾空白和可能的引号）
        title: str = full_content.strip()

        # 移除可能的引号
        for quote in ['"', "'", '"', '"', ''', ''']:
            if title.startswith(quote) and title.endswith(quote):
                title = title[1:-1]
                break

        return title
