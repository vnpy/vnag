"""调用真实 Bedrock 的可选集成测试。

默认跳过。设置 VNAG_BEDROCK_LIVE=1 后，使用 VNAG 的 connect_bedrock.json
（区域、代理、密钥）跑一轮 set_targets 工具调用，确认第二轮请求被服务端接受。

模型列表可用 VNAG_BEDROCK_MODELS 覆盖，逗号分隔。未设置时从账号的
system inference profile 里挑选 Opus 5.5、Fable 5.1、gpt-5.6-sol、grok-4.7。
"""

import os
import unittest
from typing import Any
from uuid import uuid4

from botocore.exceptions import ClientError, ParamValidationError

from vnag.agent import TaskAgent
from vnag.constant import Role
from vnag.gateways.bedrock_gateway import BedrockGateway
from vnag.local import LocalTool
from vnag.object import Message, Profile, Request, Session, ToolCall, ToolResult, ToolSchema
from vnag.utility import load_json


LIVE_FLAG: str = "VNAG_BEDROCK_LIVE"
MODEL_FLAG: str = "VNAG_BEDROCK_MODELS"

MODEL_FRAGMENTS: tuple[str, ...] = (
    "claude-opus-5-5",
    "claude-fable-5-1",
    "gpt-5.6-sol",
    "grok-4.7",
)

PREFIX_RANK: tuple[str, ...] = ("global.", "apac.", "jp.", "us.")

FALLBACK_MODELS: tuple[str, ...] = (
    "global.anthropic.claude-opus-5-5",
    "global.anthropic.claude-fable-5-1",
    "global.openai.gpt-5.6-sol",
    "global.xai.grok-4.7",
)

UNAVAILABLE_MARKERS: tuple[str, ...] = (
    "access denied",
    "not authorized",
    "could not find",
    "model identifier is invalid",
    "inference profile",
    "resource not found",
    "on-demand throughput",
    "don't have access",
    "not subscribed",
    "is not available",
)


class ModelUnavailable(Exception):
    """模型在当前区域未开通，或推理配置 ID 不存在。"""


class TargetSink:
    """记录 set_targets 是否真的被执行。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def set_targets(self, targets: dict[str, dict[str, Any]]) -> str:
        """Submit trading targets for one or more symbols."""
        self.calls.append(targets)
        return f"Trading targets updated: {targets}"


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


def _error_text(exc: BaseException) -> str:
    """取出服务端错误码和消息，不带请求凭证。"""
    response: Any = getattr(exc, "response", None)
    if isinstance(response, dict):
        error: dict[str, Any] = response.get("Error", {})
        code: str = str(error.get("Code", ""))
        message: str = str(error.get("Message", ""))
        return f"{code}: {message}".strip(": ")
    return f"{type(exc).__name__}: {exc}"


def _is_unavailable(exc: BaseException) -> bool:
    text: str = _error_text(exc).lower()
    return any(marker in text for marker in UNAVAILABLE_MARKERS)


def _models_from_env() -> list[str]:
    raw: str = os.environ.get(MODEL_FLAG, "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _rank_profile(model_id: str) -> tuple[int, int]:
    normalized: str = model_id.lower()
    for index, prefix in enumerate(PREFIX_RANK):
        if normalized.startswith(prefix):
            return index, len(model_id)
    return len(PREFIX_RANK), len(model_id)


def _candidates_for(profile_ids: list[str], fragment: str) -> list[str]:
    """同一模型的候选推理配置，优先 global，其次区域前缀。"""
    matches: list[str] = sorted(
        (
            profile_id
            for profile_id in profile_ids
            if fragment in profile_id.lower()
        ),
        key=_rank_profile,
    )
    fallback: str = next(model for model in FALLBACK_MODELS if fragment in model)
    if fallback not in matches:
        matches.append(fallback)
    return matches


def _discover_profile_ids(gateway: BedrockGateway) -> list[str]:
    """读取账号中的 system inference profile ID。失败时返回空列表。"""
    if gateway.meta_client is None:
        return []

    profile_ids: list[str] = []
    try:
        paginator: Any = gateway.meta_client.get_paginator("list_inference_profiles")
        for page in paginator.paginate(typeEquals="SYSTEM_DEFINED"):
            for summary in page.get("inferenceProfileSummaries", []):
                profile_id: str = str(summary.get("inferenceProfileId", ""))
                if profile_id:
                    profile_ids.append(profile_id)
    except Exception:
        return []
    return profile_ids


def _signature_only_count(messages: list[Message]) -> int:
    count: int = 0
    for message in messages:
        if message.role != Role.ASSISTANT:
            continue
        for item in message.reasoning:
            has_signature: bool = bool(item.get("signature"))
            has_text: bool = bool(item.get("text"))
            has_redacted: bool = item.get("redacted_content") is not None
            if has_signature and not has_text and not has_redacted:
                count += 1
    return count


def _redacted_count(messages: list[Message]) -> int:
    count: int = 0
    for message in messages:
        if message.role != Role.ASSISTANT:
            continue
        for item in message.reasoning:
            if item.get("redacted_content") is not None and not item.get("signature"):
                count += 1
    return count


def _completed_second_round(messages: list[Message]) -> bool:
    tool_index: int | None = None
    for index, message in enumerate(messages):
        if message.tool_results:
            tool_index = index
            break
    if tool_index is None:
        return False
    return any(message.role == Role.ASSISTANT for message in messages[tool_index + 1:])


@unittest.skipUnless(
    os.environ.get(LIVE_FLAG) == "1",
    "set VNAG_BEDROCK_LIVE=1 to call Bedrock",
)
class BedrockLiveTest(unittest.TestCase):
    gateway: BedrockGateway
    models: list[str]
    profile_ids: list[str]
    _previous_token: str | None

    @classmethod
    def setUpClass(cls) -> None:
        setting: dict[str, Any] = load_json("connect_bedrock.json")
        if not setting.get("region_name") or not setting.get("api_key"):
            raise unittest.SkipTest("connect_bedrock.json 缺少 region_name 或 api_key")

        cls._previous_token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
        cls.gateway = BedrockGateway()
        if not cls.gateway.init(setting):
            raise AssertionError("BedrockGateway.init 失败，请检查区域、代理和密钥")

        configured: list[str] = _models_from_env()
        cls.profile_ids = [] if configured else _discover_profile_ids(cls.gateway)
        cls.models = configured

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._previous_token is None:
            os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)
        else:
            os.environ["AWS_BEARER_TOKEN_BEDROCK"] = cls._previous_token

    def _run_once(self, model_id: str, tool: LocalTool, sink: TargetSink) -> TaskAgent:
        profile = Profile(
            name="AI Trader",
            prompt="You are a trading agent. Use tools for decisions. Be brief.",
            tools=[tool.name],
            max_tokens=8192,
            max_iterations=4,
        )
        session = Session(
            id=uuid4().hex,
            profile=profile.name,
            name="live-decision",
        )
        agent = TaskAgent(
            GatewayEngine(self.gateway, tool),
            profile,
            session,
            save=False,
        )
        agent.set_model(model_id)
        prompt: str = (
            f"Call the tool named {tool.name} exactly once now. "
            "The targets argument must be a JSON object with one key, "
            "BTC-PERP, whose value is an object with direction set to 1. "
            "Do not answer in plain text before the tool returns."
        )
        try:
            agent.invoke(prompt)
        except ParamValidationError:
            raise
        except ClientError as exc:
            if _is_unavailable(exc):
                raise ModelUnavailable(_error_text(exc)) from exc
            raise AssertionError(f"{model_id}: {_error_text(exc)}") from exc
        return agent

    def test_multiturn_set_targets_against_bedrock(self) -> None:
        sink = TargetSink()
        tool = LocalTool(sink.set_targets)
        failures: list[str] = []
        unavailable: list[str] = []
        model_groups: list[list[str]] = (
            [[model_id] for model_id in self.models]
            if self.models
            else [_candidates_for(self.profile_ids, fragment) for fragment in MODEL_FRAGMENTS]
        )

        for candidates in model_groups:
            group_unavailable: list[str] = []
            hard_failure = False
            succeeded = False
            for model_id in candidates:
                sink.calls.clear()
                agent: TaskAgent | None = None
                try:
                    agent = self._run_once(model_id, tool, sink)
                    if not sink.calls:
                        agent = self._run_once(model_id, tool, sink)
                except ModelUnavailable as exc:
                    group_unavailable.append(f"{model_id}: {exc}")
                    continue
                except Exception as exc:
                    failures.append(f"{model_id}: {exc}")
                    hard_failure = True
                    break

                if (
                    agent is not None
                    and sink.calls
                    and _completed_second_round(agent.messages)
                ):
                    print(
                        f"{model_id}: targets={sink.calls[-1]} "
                        f"signature_only={_signature_only_count(agent.messages)} "
                        f"redacted={_redacted_count(agent.messages)}"
                    )
                    succeeded = True
                    break

                failures.append(f"{model_id}: 模型没有完成 set_targets 后的第二轮请求")
                hard_failure = True
                break

            if not succeeded and not hard_failure:
                unavailable.extend(group_unavailable)

        problems: list[str] = failures + unavailable
        if problems:
            self.fail("\n".join(problems))


if __name__ == "__main__":
    unittest.main()
