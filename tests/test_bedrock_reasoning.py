import json
import unittest
import base64
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from botocore.session import Session as BotocoreSession
from botocore.validate import ParamValidator

from vnag.agent import TaskAgent
from vnag.constant import Role
from vnag.gateways.bedrock_gateway import BedrockGateway
from vnag.local import LocalTool
from vnag.object import Message, Profile, Request, Session, ToolCall, ToolResult, ToolSchema


def _converse_stream_shape() -> Any:
    """加载当前 botocore 的 ConverseStream 入参形状。"""
    service = BotocoreSession().get_service_model("bedrock-runtime")
    return service.operation_model("ConverseStream").input_shape


def _validation_report(params: dict[str, Any]) -> str:
    """返回 ConverseStream 入参的校验报告；通过时为空字符串。"""
    errors = ParamValidator().validate(params, _converse_stream_shape())
    if not errors.has_errors():
        return ""
    return str(errors.generate_report())


class TargetSink:
    """记录 set_targets 是否真的被执行。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def set_targets(self, targets: dict[str, dict[str, Any]]) -> str:
        """Update trading targets."""
        self.calls.append(targets)
        return f"Trading targets updated: {targets}"


class ScriptedBedrockClient:
    """按脚本返回 converse_stream 事件，并记下每次请求。"""

    def __init__(self, streams: list[list[dict[str, Any]]]) -> None:
        self._streams: list[list[dict[str, Any]]] = list(streams)
        self.calls: list[dict[str, Any]] = []

    def converse_stream(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        events: list[dict[str, Any]] = self._streams.pop(0)
        return {
            "ResponseMetadata": {"RequestId": f"req-{len(self.calls)}"},
            "stream": events,
        }


class GatewayEngine:
    """只把 TaskAgent 接到 BedrockGateway 和一个本地工具上。"""

    def __init__(self, gateway: BedrockGateway, tool: LocalTool) -> None:
        self.gateway: BedrockGateway = gateway
        self.tool: LocalTool = tool

    def get_tool_schemas(self, tools: list[str] | None = None) -> list[ToolSchema]:
        schema: ToolSchema = self.tool.get_schema()
        if tools is not None and schema.name not in tools:
            return []
        return [schema]

    def get_skill_schema(self) -> None:
        return None

    def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        try:
            content: str = str(self.tool.function(**tool_call.arguments))
            is_error = False
        except Exception as exc:
            content = f"{type(exc).__name__}: {exc}"
            is_error = True
        return ToolResult(
            id=tool_call.id,
            name=tool_call.name,
            content=content,
            is_error=is_error,
        )

    def stream(self, request: Request) -> Any:
        return self.gateway.stream(request)


def _reasoning_deltas(
    chunks: list[tuple[int, dict[str, Any]]]
) -> list[dict[str, Any]]:
    return [
        {
            "contentBlockDelta": {
                "contentBlockIndex": index,
                "delta": {"reasoningContent": payload},
            }
        }
        for index, payload in chunks
    ]


def _closed_reasoning_events(
    chunks: list[tuple[int, dict[str, Any]]]
) -> list[dict[str, Any]]:
    """推理增量按块结束后补上 contentBlockStop。"""
    events: list[dict[str, Any]] = []
    last_index: int | None = None
    for index, payload in chunks:
        if last_index is not None and index != last_index:
            events.append({"contentBlockStop": {"contentBlockIndex": last_index}})
        events.extend(_reasoning_deltas([(index, payload)]))
        last_index = index
    if last_index is not None:
        events.append({"contentBlockStop": {"contentBlockIndex": last_index}})
    return events


def _tool_round_events(
    tool_name: str,
    reasoning_chunks: list[tuple[int, dict[str, Any]]],
) -> list[dict[str, Any]]:
    """第一轮：完整推理块，然后调用 set_targets。"""
    tool_input: str = json.dumps({"targets": {"BTC-PERP": {"direction": 1}}})
    return [
        *_closed_reasoning_events(reasoning_chunks),
        {
            "contentBlockStart": {
                "contentBlockIndex": 2,
                "start": {
                    "toolUse": {
                        "toolUseId": "tool-1",
                        "name": tool_name,
                    }
                },
            }
        },
        {
            "contentBlockDelta": {
                "contentBlockIndex": 2,
                "delta": {"toolUse": {"input": tool_input}},
            }
        },
        {"messageStop": {"stopReason": "tool_use"}},
        {"metadata": {"usage": {"inputTokens": 12, "outputTokens": 8}}},
    ]


def _final_events() -> list[dict[str, Any]]:
    """第二轮：模型结束，不再调用工具。"""
    return [
        {
            "contentBlockDelta": {
                "contentBlockIndex": 0,
                "delta": {"text": "done"},
            }
        },
        {"messageStop": {"stopReason": "end_turn"}},
        {"metadata": {"usage": {"inputTokens": 30, "outputTokens": 4}}},
    ]


def _signature_streams(tool_name: str) -> list[list[dict[str, Any]]]:
    """带文本的思考块，加上单独的只有 signature 的思考块。"""
    return [
        _tool_round_events(
            tool_name,
            [
                (0, {"text": "check positions"}),
                (0, {"signature": "sig-text-block"}),
                (1, {"signature": "sig-only-block"}),
            ],
        ),
        _final_events(),
    ]


def _redacted_streams(tool_name: str) -> list[list[dict[str, Any]]]:
    """同一推理块上的两段密文增量。"""
    return [
        _tool_round_events(
            tool_name,
            [
                (0, {"redactedContent": b"chunk-a"}),
                (0, {"redactedContent": b"chunk-b"}),
            ],
        ),
        _final_events(),
    ]


class BedrockReasoningTest(unittest.TestCase):
    def _invoke(
        self,
        model_id: str,
        stream_factory: Any,
        thinking_mode: str = "adaptive",
    ) -> tuple[ScriptedBedrockClient, TargetSink, Any]:
        sink = TargetSink()
        tool = LocalTool(sink.set_targets)
        gateway = BedrockGateway()
        gateway.thinking_mode = thinking_mode
        gateway.thinking_effort = "medium"
        client = ScriptedBedrockClient(stream_factory(tool.name))
        gateway.client = client

        profile = Profile(
            name="AI Trader",
            prompt="trade",
            tools=[tool.name],
            max_iterations=4,
        )
        session = Session(
            id=uuid4().hex,
            profile=profile.name,
            name="decision",
        )
        agent = TaskAgent(
            GatewayEngine(gateway, tool),
            profile,
            session,
            save=False,
        )
        agent.set_model(model_id)
        response = agent.invoke("set targets")
        return client, sink, response

    def _assert_valid(self, params: dict[str, Any]) -> None:
        report: str = _validation_report(params)
        self.assertEqual(report, "")

    def test_validator_rejects_signature_without_text(self) -> None:
        """确认本机 botocore 仍会拒绝用户遇到的缺 text 形状。"""
        params: dict[str, Any] = {
            "modelId": "anthropic.claude-opus-5",
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {
                            "reasoningContent": {
                                "reasoningText": {"signature": "sig-only"}
                            }
                        }
                    ],
                }
            ],
        }
        report: str = _validation_report(params)
        self.assertIn(
            'reasoningContent.reasoningText: "text"',
            report,
        )

    def test_signature_only_block_replays_empty_text(self) -> None:
        gateway = BedrockGateway()
        message = Message(
            role=Role.ASSISTANT,
            reasoning=[
                {"index": 0, "type": "reasoning", "signature": "sig-only"},
                {
                    "index": 1,
                    "type": "reasoning",
                    "text": "",
                    "signature": "sig-empty",
                },
            ],
        )

        _, converted = gateway._convert_messages([message])
        blocks: list[dict[str, Any]] = converted[0]["content"]

        self.assertEqual(
            blocks[0]["reasoningContent"]["reasoningText"],
            {"text": "", "signature": "sig-only"},
        )
        self.assertEqual(
            blocks[1]["reasoningContent"]["reasoningText"],
            {"text": "", "signature": "sig-empty"},
        )
        self._assert_valid({
            "modelId": "anthropic.claude-opus-5",
            "messages": converted,
        })

    def test_nonempty_reasoning_text_and_signature_round_trip(self) -> None:
        gateway = BedrockGateway()
        message = Message(
            role=Role.ASSISTANT,
            content="answer",
            reasoning=[
                {
                    "index": 0,
                    "type": "reasoning",
                    "text": "think hard",
                    "signature": "sig-full",
                }
            ],
            tool_calls=[
                ToolCall(
                    id="tool-1",
                    name="set-targets",
                    arguments={"targets": {"BTC-PERP": {"direction": 1}}},
                )
            ],
        )

        _, converted = gateway._convert_messages([message])
        blocks: list[dict[str, Any]] = converted[0]["content"]

        self.assertEqual(
            blocks[0]["reasoningContent"]["reasoningText"],
            {"text": "think hard", "signature": "sig-full"},
        )
        self.assertEqual(blocks[1], {"text": "answer"})
        self.assertEqual(blocks[2]["toolUse"]["toolUseId"], "tool-1")
        self.assertNotIn("redactedContent", blocks[0]["reasoningContent"])
        self._assert_valid({
            "modelId": "anthropic.claude-opus-4-5",
            "messages": converted,
        })

    def test_redacted_content_replays_without_reasoning_text(self) -> None:
        gateway = BedrockGateway()
        message = Message(
            role=Role.ASSISTANT,
            reasoning=[{"index": 0, "type": "reasoning", "redacted_content": b"cipher"}],
        )

        _, converted = gateway._convert_messages([message])
        reasoning: dict[str, Any] = converted[0]["content"][0]["reasoningContent"]

        self.assertEqual(reasoning, {"redactedContent": b"cipher"})
        self.assertNotIn("reasoningText", reasoning)
        self._assert_valid({
            "modelId": "openai.gpt-5.6-sol",
            "messages": converted,
        })

    def _assert_signature_replay(self, call: dict[str, Any]) -> None:
        assistant = next(
            message for message in call["messages"] if message["role"] == "assistant"
        )
        blocks: list[dict[str, Any]] = assistant["content"]
        reasoning_blocks: list[dict[str, Any]] = [
            block["reasoningContent"] for block in blocks if "reasoningContent" in block
        ]

        self.assertEqual(
            reasoning_blocks[0]["reasoningText"],
            {"text": "check positions", "signature": "sig-text-block"},
        )
        self.assertEqual(
            reasoning_blocks[1]["reasoningText"],
            {"text": "", "signature": "sig-only-block"},
        )
        self.assertEqual(blocks[-1]["toolUse"]["toolUseId"], "tool-1")

        tool_result_message = call["messages"][-1]
        self.assertEqual(tool_result_message["role"], "user")
        tool_result: dict[str, Any] = tool_result_message["content"][0]["toolResult"]
        self.assertEqual(tool_result["toolUseId"], "tool-1")
        self.assertIn("Trading targets updated", tool_result["content"][0]["text"])
        self._assert_valid(call)

    def _assert_adaptive_fields(self, call: dict[str, Any]) -> None:
        fields: dict[str, Any] = call["additionalModelRequestFields"]
        self.assertEqual(fields["thinking"], {"type": "adaptive"})
        self.assertEqual(fields["output_config"], {"effort": "medium"})
        self.assertNotIn("budget_tokens", fields["thinking"])

    def test_opus_5_multiturn_set_targets_replays_empty_reasoning_text(self) -> None:
        client, sink, response = self._invoke(
            "us.anthropic.claude-opus-5",
            _signature_streams,
        )

        self.assertEqual(response.content, "done")
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(sink.calls, [{"BTC-PERP": {"direction": 1}}])
        self._assert_adaptive_fields(client.calls[0])
        self._assert_adaptive_fields(client.calls[1])
        self._assert_signature_replay(client.calls[1])
        self._assert_valid(client.calls[0])

    def test_opus_5_5_and_fable_5_1_complete_tool_round(self) -> None:
        model_ids: list[str] = [
            "global.anthropic.claude-opus-5-5",
            "global.anthropic.claude-fable-5-1",
        ]
        for model_id in model_ids:
            with self.subTest(model_id=model_id):
                client, sink, response = self._invoke(model_id, _signature_streams)

                self.assertEqual(response.content, "done")
                self.assertEqual(sink.calls, [{"BTC-PERP": {"direction": 1}}])
                self.assertEqual(len(client.calls), 2)
                for call in client.calls:
                    self._assert_adaptive_fields(call)
                    self._assert_valid(call)
                self._assert_signature_replay(client.calls[1])

    def test_fable_5_1_disabled_mode_still_sends_adaptive(self) -> None:
        client, sink, response = self._invoke(
            "us.anthropic.claude-fable-5-1",
            _signature_streams,
            thinking_mode="disabled",
        )

        self.assertEqual(response.content, "done")
        self.assertEqual(len(sink.calls), 1)
        for call in client.calls:
            self._assert_adaptive_fields(call)
            self._assert_valid(call)
        self._assert_signature_replay(client.calls[1])

    def test_opus_5_5_disabled_thinking_stays_disabled(self) -> None:
        gateway = BedrockGateway()
        gateway.thinking_mode = "disabled"
        gateway.thinking_effort = "medium"

        fields = gateway._get_additional_model_request_fields(
            "us.anthropic.claude-opus-5-5"
        )

        self.assertIsNotNone(fields)
        assert fields is not None
        self.assertEqual(fields["thinking"], {"type": "disabled"})
        self.assertEqual(fields["output_config"], {"effort": "medium"})

    def test_gpt_5_6_and_grok_replay_concatenated_redacted_content(self) -> None:
        model_ids: list[str] = [
            "global.openai.gpt-5.6-sol",
            "global.xai.grok-4.7",
        ]
        for model_id in model_ids:
            with self.subTest(model_id=model_id):
                client, sink, response = self._invoke(model_id, _redacted_streams)

                self.assertEqual(response.content, "done")
                self.assertEqual(sink.calls, [{"BTC-PERP": {"direction": 1}}])
                self.assertEqual(len(client.calls), 2)
                for call in client.calls:
                    self.assertNotIn("additionalModelRequestFields", call)
                    self._assert_valid(call)

                assistant = next(
                    message
                    for message in client.calls[1]["messages"]
                    if message["role"] == "assistant"
                )
                reasoning: dict[str, Any] = assistant["content"][0]["reasoningContent"]
                self.assertEqual(reasoning, {"redactedContent": b"chunk-achunk-b"})
                self.assertNotIn("reasoningText", reasoning)

    def test_opus_4_5_keeps_budget_tokens(self) -> None:
        gateway = BedrockGateway()
        fields = gateway._get_additional_model_request_fields(
            "us.anthropic.claude-opus-4-5"
        )

        self.assertIsNotNone(fields)
        assert fields is not None
        self.assertEqual(fields["thinking"]["type"], "enabled")
        self.assertEqual(fields["thinking"]["budget_tokens"], 2000)
        self.assertNotIn("output_config", fields)

        client, sink, response = self._invoke(
            "us.anthropic.claude-opus-4-5",
            lambda tool_name: [_final_events()],
        )

        self.assertEqual(response.content, "done")
        self.assertEqual(sink.calls, [])
        self.assertEqual(len(client.calls), 1)
        thinking: dict[str, Any] = client.calls[0]["additionalModelRequestFields"]["thinking"]
        self.assertEqual(thinking["type"], "enabled")
        self.assertEqual(thinking["budget_tokens"], 2000)
        self._assert_valid(client.calls[0])

    def test_saved_session_roundtrips_redacted_content(self) -> None:
        sink = TargetSink()
        tool = LocalTool(sink.set_targets)
        gateway = BedrockGateway()
        gateway.client = ScriptedBedrockClient(_redacted_streams(tool.name))
        profile = Profile(
            name="AI Trader",
            prompt="trade",
            tools=[tool.name],
            max_iterations=4,
        )
        session = Session(
            id="redacted-save",
            profile=profile.name,
            name="decision",
        )

        with TemporaryDirectory() as temp_dir:
            with patch("vnag.agent.SESSION_DIR", Path(temp_dir)):
                agent = TaskAgent(
                    GatewayEngine(gateway, tool),
                    profile,
                    session,
                    save=True,
                )
                agent.set_model("global.openai.gpt-5.6-sol")
                agent.invoke("set targets")
                saved_path = Path(temp_dir).joinpath("redacted-save.json")
                saved: dict[str, Any] = json.loads(
                    saved_path.read_text(encoding="utf-8")
                )

        redacted_values: list[str] = []
        for message in saved["messages"]:
            if message["role"] != Role.ASSISTANT.value:
                continue
            for item in message["reasoning"]:
                if "redacted_content" in item:
                    redacted_values.append(item["redacted_content"])

        self.assertEqual(redacted_values, [base64.b64encode(b"chunk-achunk-b").decode("ascii")])
        restored = Session.model_validate(saved)
        _, converted = gateway._convert_messages(restored.messages)
        assistant = next(message for message in converted if message["role"] == "assistant")
        self.assertEqual(
            assistant["content"][0]["reasoningContent"],
            {"redactedContent": b"chunk-achunk-b"},
        )

    def test_unclosed_reasoning_block_is_not_replayed(self) -> None:
        events: list[dict[str, Any]] = [
            *_reasoning_deltas([
                (0, {"text": "check positions"}),
                (0, {"signature": "sig-only-block"}),
            ]),
            {"messageStop": {"stopReason": "end_turn"}},
        ]
        gateway = BedrockGateway()
        gateway.client = ScriptedBedrockClient([events])
        deltas = list(gateway.stream(Request(
            model="us.anthropic.claude-opus-5",
            messages=[Message(role=Role.USER, content="decide")],
        )))
        self.assertTrue(any(delta.thinking for delta in deltas))
        self.assertFalse(any(delta.reasoning for delta in deltas))

        sink = TargetSink()
        tool = LocalTool(sink.set_targets)
        gateway.client = ScriptedBedrockClient([events])
        profile = Profile(
            name="AI Trader",
            prompt="trade",
            tools=[tool.name],
            max_iterations=2,
        )
        session = Session(id=uuid4().hex, profile=profile.name, name="partial")
        agent = TaskAgent(
            GatewayEngine(gateway, tool),
            profile,
            session,
            save=False,
        )
        agent.set_model("us.anthropic.claude-opus-5")
        generator = agent.stream("decide")
        next(generator)
        agent.abort_stream()
        generator.close()

        self.assertFalse(any(message.reasoning for message in agent.messages))
        _, converted = gateway._convert_messages(agent.messages)
        for message in converted:
            for block in message["content"]:
                self.assertNotIn("reasoningContent", block)


if __name__ == "__main__":
    unittest.main()
