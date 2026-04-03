from typing import Any
from uuid import uuid4
from collections.abc import Generator

from ollama import Client

from vnag.constant import FinishReason, Role
from vnag.gateway import BaseGateway
from vnag.object import Request, Response, Delta, Usage, Message, ToolCall


OLLAMA_FINISH_REASON_MAP: dict[str, FinishReason] = {
    "stop": FinishReason.STOP,
    "length": FinishReason.LENGTH,
    "load": FinishReason.STOP,
    "unload": FinishReason.STOP,
}


class OllamaGateway(BaseGateway):
    """
    Ollama 原生 SDK 网关

    使用 ollama Python SDK 连接本地或云端 Ollama 服务，支持：
    - thinking 字段的提取和流式输出
    - 将 thinking 转换为内部 reasoning 结构，便于跨轮持久化
    - 工具调用和工具结果回传
    - 模型列表查询

    reasoning 策略：
    - UI 展示使用 `thinking` 字段
    - 会话持久化和跨轮恢复使用 `reasoning` 列表
    - assistant 历史消息会原样回传 thinking，以支持交错思维链
    """

    default_name: str = "Ollama"

    default_setting: dict = {
        "host": "http://localhost:11434",
        "api_key": "",
        "proxy": "",
        "thinking_level": ["high", "medium", "low"],
        "keep_alive": "5m",
    }

    def __init__(self, gateway_name: str = "") -> None:
        """构造函数"""
        if not gateway_name:
            gateway_name = self.default_name
        self.gateway_name = gateway_name

        self.client: Client | None = None
        self.thinking_level: str = "medium"
        self.keep_alive: str | int = "5m"

    def _get_message_thinking(self, msg: Message) -> str:
        """
        获取消息中的 thinking 内容

        优先使用 Message.thinking；若为空，则尝试从内部 reasoning
        结构中恢复 Ollama thinking 文本。
        """
        if msg.thinking:
            return msg.thinking

        parts: list[str] = []
        for item in msg.reasoning:
            if item.get("type") != "ollama_thinking":
                continue

            text: Any = item.get("text")
            if isinstance(text, str) and text:
                parts.append(text)

        return "".join(parts)

    def _build_reasoning_items(self, thinking: str) -> list[dict[str, Any]]:
        """将 thinking 文本封装为内部 reasoning 结构"""
        if not thinking:
            return []

        return [{
            "index": 0,
            "type": "ollama_thinking",
            "format": "text",
            "text": thinking,
        }]

    def _convert_tool_calls(
        self, tool_calls: list[ToolCall]
    ) -> list[dict[str, Any]]:
        """将内部工具调用格式转换为 Ollama 消息格式"""
        return [
            {
                "function": {
                    "name": tc.name,
                    "arguments": tc.arguments,
                }
            }
            for tc in tool_calls
        ]

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """
        将内部 Message 格式转换为 Ollama chat messages

        重要约束：
        - tool_results 需拆分为多条 tool 角色消息，并使用 tool_name
        - assistant 历史消息需要回传 thinking，以保持交错思维链连续性
        """
        ollama_messages: list[dict[str, Any]] = []

        for msg in messages:
            if msg.tool_results:
                for tool_result in msg.tool_results:
                    ollama_messages.append({
                        "role": "tool",
                        "tool_name": tool_result.name,
                        "content": tool_result.content,
                    })
                continue

            message_dict: dict[str, Any] = {"role": msg.role.value}

            if msg.role == Role.ASSISTANT:
                thinking: str = self._get_message_thinking(msg)
                if msg.content or thinking or msg.tool_calls:
                    message_dict["content"] = msg.content or ""
                if thinking:
                    message_dict["thinking"] = thinking
                if msg.tool_calls:
                    message_dict["tool_calls"] = self._convert_tool_calls(
                        msg.tool_calls
                    )
                if len(message_dict) > 1:
                    ollama_messages.append(message_dict)
                continue

            if msg.content:
                message_dict["content"] = msg.content
                ollama_messages.append(message_dict)

        return ollama_messages

    def _resolve_think(self, model: str) -> bool | str:
        """根据模型名称计算 Ollama 的 think 参数（thinking 始终开启）"""
        model_name: str = model.lower()
        if "gpt-oss" in model_name:
            return self.thinking_level

        return True

    def _build_options(self, request: Request) -> dict[str, Any] | None:
        """构建 Ollama options 参数"""
        options: dict[str, Any] = {}

        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.top_p is not None:
            options["top_p"] = request.top_p
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens

        return options if options else None

    def _parse_tool_calls(self, message: Any, response_id: str) -> list[ToolCall]:
        """从 Ollama message 中提取工具调用"""
        raw_tool_calls: Any = getattr(message, "tool_calls", None)
        if not raw_tool_calls:
            return []

        tool_calls: list[ToolCall] = []
        for index, raw_tool_call in enumerate(raw_tool_calls):
            function: Any = getattr(raw_tool_call, "function", None)
            if not function:
                continue

            name: str = getattr(function, "name", "") or ""
            raw_arguments: Any = getattr(function, "arguments", None)

            arguments: dict[str, Any] = {}
            if isinstance(raw_arguments, dict):
                arguments = raw_arguments
            elif raw_arguments:
                try:
                    arguments = dict(raw_arguments)
                except (TypeError, ValueError):
                    arguments = {}

            tool_calls.append(ToolCall(
                id=f"ollama-call-{response_id}-{index}",
                name=name,
                arguments=arguments,
            ))

        return tool_calls

    def _get_finish_reason(self, done_reason: str | None, has_tool_calls: bool) -> FinishReason:
        """将 Ollama done_reason 映射为内部 FinishReason"""
        if has_tool_calls:
            return FinishReason.TOOL_CALLS

        if not done_reason:
            return FinishReason.UNKNOWN

        return OLLAMA_FINISH_REASON_MAP.get(
            done_reason, FinishReason.UNKNOWN
        )

    def init(self, setting: dict[str, Any]) -> bool:
        """初始化连接和内部服务组件，返回是否成功。"""
        host: str = setting.get("host", "http://localhost:11434")
        api_key: str = setting.get("api_key", "")
        proxy: str = setting.get("proxy", "")

        if not host:
            self.write_log("配置不完整，请检查以下配置项：")
            self.write_log("  - host: Ollama 服务地址未设置")
            return False

        self.thinking_level = setting.get("thinking_level", "medium")
        self.keep_alive = setting.get("keep_alive", "5m")

        client_kwargs: dict[str, Any] = {"host": host}
        if api_key:
            client_kwargs["headers"] = {
                "Authorization": f"Bearer {api_key}"
            }
        if proxy:
            client_kwargs["proxy"] = proxy

        try:
            self.client = Client(**client_kwargs)
        except Exception as e:
            self.write_log(f"创建 Ollama 客户端失败: {e}")
            return False

        return True

    def invoke(self, request: Request) -> Response:
        """常规调用接口：将已准备好的消息发送给模型并一次性产出文本。"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return Response(id="", content="", usage=Usage())

        response_id: str = str(uuid4())
        ollama_messages: list[dict[str, Any]] = self._convert_messages(
            request.messages
        )

        chat_params: dict[str, Any] = {
            "model": request.model,
            "messages": ollama_messages,
            "think": self._resolve_think(request.model),
            "stream": False,
            "keep_alive": self.keep_alive,
        }

        options: dict[str, Any] | None = self._build_options(request)
        if options:
            chat_params["options"] = options

        if request.tool_schemas:
            chat_params["tools"] = [t.get_schema() for t in request.tool_schemas]

        try:
            response: Any = self.client.chat(**chat_params)
        except Exception as e:
            self.write_log(f"Ollama 调用失败: {e}")
            return Response(id=response_id, content="", usage=Usage())

        message: Any = getattr(response, "message", None)
        content: str = getattr(message, "content", "") or ""
        thinking: str = getattr(message, "thinking", "") or ""
        reasoning: list[dict[str, Any]] = self._build_reasoning_items(thinking)
        tool_calls: list[ToolCall] = self._parse_tool_calls(message, response_id)

        usage: Usage = Usage(
            input_tokens=getattr(response, "prompt_eval_count", 0) or 0,
            output_tokens=getattr(response, "eval_count", 0) or 0,
        )

        finish_reason: FinishReason = self._get_finish_reason(
            getattr(response, "done_reason", None),
            has_tool_calls=bool(tool_calls),
        )

        assistant_message: Message = Message(
            role=Role.ASSISTANT,
            content=content,
            thinking=thinking,
            reasoning=reasoning,
            tool_calls=tool_calls,
        )

        return Response(
            id=response_id,
            content=content,
            thinking=thinking,
            usage=usage,
            finish_reason=finish_reason,
            message=assistant_message,
        )

    def stream(self, request: Request) -> Generator[Delta, None, None]:
        """流式调用接口"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return

        response_id: str = str(uuid4())
        ollama_messages: list[dict[str, Any]] = self._convert_messages(
            request.messages
        )

        chat_params: dict[str, Any] = {
            "model": request.model,
            "messages": ollama_messages,
            "think": self._resolve_think(request.model),
            "stream": True,
            "keep_alive": self.keep_alive,
        }

        options: dict[str, Any] | None = self._build_options(request)
        if options:
            chat_params["options"] = options

        if request.tool_schemas:
            chat_params["tools"] = [t.get_schema() for t in request.tool_schemas]

        try:
            stream: Any = self.client.chat(**chat_params)
        except Exception as e:
            self.write_log(f"Ollama 流式调用失败: {e}")
            return

        accumulated_tool_calls: list[ToolCall] = []

        for chunk in stream:
            delta: Delta = Delta(id=response_id)
            should_yield: bool = False

            message: Any = getattr(chunk, "message", None)
            if message:
                thinking_delta: str = getattr(message, "thinking", "") or ""
                if thinking_delta:
                    delta.thinking = thinking_delta
                    delta.reasoning = self._build_reasoning_items(thinking_delta)
                    should_yield = True

                content_delta: str = getattr(message, "content", "") or ""
                if content_delta:
                    delta.content = content_delta
                    should_yield = True

                if getattr(message, "tool_calls", None):
                    accumulated_tool_calls = self._parse_tool_calls(
                        message, response_id
                    )

            if getattr(chunk, "done", False):
                delta.usage = Usage(
                    input_tokens=getattr(chunk, "prompt_eval_count", 0) or 0,
                    output_tokens=getattr(chunk, "eval_count", 0) or 0,
                )
                delta.finish_reason = self._get_finish_reason(
                    getattr(chunk, "done_reason", None),
                    has_tool_calls=bool(accumulated_tool_calls),
                )
                if accumulated_tool_calls:
                    delta.tool_calls = accumulated_tool_calls
                should_yield = True

            if should_yield:
                yield delta

    def list_models(self) -> list[str]:
        """查询可用模型列表"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return []

        try:
            response: Any = self.client.list()
        except Exception as e:
            self.write_log(f"查询 Ollama 模型列表失败: {e}")
            return []

        model_names: set[str] = set()
        for item in getattr(response, "models", []):
            model_name: str = getattr(item, "model", "") or ""
            if model_name:
                model_names.add(model_name)

        return sorted(model_names)
