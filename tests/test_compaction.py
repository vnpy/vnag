import unittest

from vnag.agent import (
    COMPACTION_MAX_TOKENS,
    SUMMARY_PREFIX,
    TaskAgent,
)
from vnag.constant import Role
from vnag.object import Delta, Message, Profile, Session, ToolResult, Usage


class FakeEngine:
    def __init__(
        self,
        fail_summary: bool = False,
        usage_values: list[int | None] | None = None,
        summary_text: str = "历史摘要",
    ) -> None:
        self.fail_summary: bool = fail_summary
        self.requests: list = []
        self.usage_values: list[int | None] = list(usage_values or [])
        self.summary_text: str = summary_text

    def get_skill_catalog(self) -> str:
        return ""

    def get_tool_schemas(self, tools: list[str] | None = None) -> list:
        return []

    def get_skill_schema(self):  # type: ignore[no-untyped-def]
        return None

    def execute_tool(self, tool_call):  # type: ignore[no-untyped-def]
        raise AssertionError("test should not execute tools")

    def stream(self, request):  # type: ignore[no-untyped-def]
        self.requests.append(request)

        # 根据摘要提示词识别压缩请求，避免将普通对话和摘要对话混淆。
        if (
            request.messages
            and "请将以上对话压缩为一段供后续继续对话使用的上下文摘要。"
            in request.messages[-1].content
        ):
            if self.fail_summary:
                raise RuntimeError("summary failed")
            text: str = self.summary_text
            usage_tokens: int | None = None
        else:
            text = "最终回答"
            usage_tokens = self.usage_values.pop(0) if self.usage_values else None

        yield Delta(id="resp", content=text)
        if usage_tokens is not None:
            yield Delta(
                id="resp",
                usage=Usage(input_tokens=usage_tokens, output_tokens=1),
            )
        yield Delta(id="resp", finish_reason="stop")


class CompactionTestCase(unittest.TestCase):
    def test_profile_and_session_defaults_are_backward_compatible(self) -> None:
        profile = Profile.model_validate({
            "name": "助手",
            "prompt": "系统提示词",
            "tools": [],
        })
        session = Session.model_validate({
            "id": "session-1",
            "profile": "助手",
            "name": "默认会话",
            "messages": [],
        })

        self.assertEqual(profile.compaction_threshold, 0)
        self.assertEqual(profile.compaction_turns, 3)
        self.assertEqual(session.summary, "")
        self.assertEqual(session.offset, 1)

    def test_agent_inserts_system_message_when_session_is_malformed(self) -> None:
        engine = FakeEngine()
        profile = Profile(name="助手", prompt="系统提示词", tools=[])
        session = Session(
            id="session-0",
            profile="助手",
            name="默认会话",
            messages=[Message(role=Role.USER, content="缺少 system")],
        )

        agent = TaskAgent(engine, profile, session, save=False)

        self.assertEqual(agent.session.messages[0].role, Role.SYSTEM)
        self.assertEqual(agent.session.messages[0].content, "系统提示词")
        self.assertEqual(agent.session.offset, 1)

    def test_stream_keeps_original_behavior_when_compaction_disabled(self) -> None:
        engine = FakeEngine()
        profile = Profile(
            name="助手",
            prompt="系统提示词",
            tools=[],
        )
        session = Session(
            id="session-1",
            profile="助手",
            name="默认会话",
            messages=[Message(role=Role.SYSTEM, content="系统提示词")],
        )
        agent = TaskAgent(engine, profile, session, save=False)

        list(agent.stream("你好"))

        self.assertEqual(agent.session.summary, "")
        self.assertEqual(agent.session.offset, 1)
        self.assertEqual(len(engine.requests), 1)
        self.assertEqual(
            [message.content for message in engine.requests[0].messages],
            ["系统提示词", "你好"],
        )

    def test_compaction_summarizes_old_messages_and_injects_summary(self) -> None:
        engine = FakeEngine()
        profile = Profile(
            name="助手",
            prompt="系统提示词",
            tools=[],
            compaction_threshold=5,
            compaction_turns=1,
            max_tokens=2048,
        )
        session = Session(
            id="session-2",
            profile="助手",
            name="默认会话",
            messages=[
                Message(role=Role.SYSTEM, content="系统提示词"),
                Message(role=Role.USER, content="旧问题一"),
                Message(role=Role.ASSISTANT, content="旧回答一"),
                Message(role=Role.USER, content="旧问题二"),
                Message(
                    role=Role.ASSISTANT,
                    content="旧回答二",
                    usage=Usage(input_tokens=6, output_tokens=1),
                ),
            ],
        )
        agent = TaskAgent(engine, profile, session, save=False)

        list(agent.stream("最新问题"))

        self.assertEqual(agent.session.summary, "历史摘要")
        self.assertEqual(agent.session.offset, 5)
        self.assertEqual(len(engine.requests), 2)

        actual_request = engine.requests[-1]
        self.assertEqual(actual_request.messages[1].role, Role.USER)
        self.assertTrue(
            actual_request.messages[1].content.startswith(SUMMARY_PREFIX)
        )
        self.assertEqual(
            [message.content for message in agent.session.messages],
            ["系统提示词", "旧问题一", "旧回答一", "旧问题二", "旧回答二", "最新问题", "最终回答"],
        )
        self.assertEqual(
            [message.content for message in actual_request.messages],
            ["系统提示词", f"{SUMMARY_PREFIX}\n历史摘要", "最新问题"],
        )
        self.assertIn(str(COMPACTION_MAX_TOKENS), engine.requests[0].messages[-1].content)
        self.assertEqual(engine.requests[0].max_tokens, profile.max_tokens)

    def test_tool_result_message_is_compacted_with_previous_turn(self) -> None:
        engine = FakeEngine()
        profile = Profile(
            name="助手",
            prompt="系统提示词",
            tools=[],
            compaction_turns=1,
        )
        session = Session(
            id="session-3",
            profile="助手",
            name="默认会话",
            messages=[
                Message(role=Role.SYSTEM, content="系统提示词"),
                Message(role=Role.USER, content="第一轮"),
                Message(role=Role.ASSISTANT, content="执行工具"),
                Message(
                    role=Role.USER,
                    tool_results=[
                        ToolResult(id="1", name="tool", content="工具结果")
                    ],
                ),
                Message(role=Role.USER, content="第二轮"),
            ],
        )
        agent = TaskAgent(engine, profile, session, save=False)

        compaction_target = agent._get_compaction_target()

        self.assertIsNotNone(compaction_target)
        messages_to_compact, preserve_start = compaction_target or ([], 0)
        self.assertEqual(preserve_start, 4)
        self.assertEqual(len(messages_to_compact), 3)
        self.assertEqual(messages_to_compact[-1].content, "")
        self.assertEqual(messages_to_compact[-1].tool_results[0].content, "工具结果")

    def test_request_messages_only_include_tail_after_offset(self) -> None:
        engine = FakeEngine()
        profile = Profile(name="助手", prompt="系统提示词", tools=[])
        session = Session(
            id="session-5",
            profile="助手",
            name="默认会话",
            messages=[
                Message(role=Role.SYSTEM, content="系统提示词"),
                Message(role=Role.USER, content="旧问题一"),
                Message(role=Role.ASSISTANT, content="旧回答一"),
                Message(role=Role.USER, content="旧问题二"),
                Message(role=Role.ASSISTANT, content="旧回答二"),
                Message(role=Role.USER, content="最近问题"),
            ],
            summary="历史摘要",
            offset=5,
        )
        agent = TaskAgent(engine, profile, session, save=False)

        request_messages = agent._get_request_messages()

        self.assertEqual(
            [message.content for message in request_messages],
            ["系统提示词", f"{SUMMARY_PREFIX}\n历史摘要", "最近问题"],
        )

    def test_compaction_can_trigger_again_with_new_usage(self) -> None:
        engine = FakeEngine()
        profile = Profile(
            name="助手",
            prompt="系统提示词",
            tools=[],
            compaction_threshold=10,
            compaction_turns=1,
        )
        session = Session(
            id="session-7",
            profile="助手",
            name="默认会话",
            messages=[
                Message(role=Role.SYSTEM, content="系统提示词"),
                Message(role=Role.USER, content="旧问题一"),
                Message(role=Role.ASSISTANT, content="旧回答一"),
                Message(role=Role.USER, content="旧问题二"),
                Message(role=Role.ASSISTANT, content="旧回答二"),
                Message(role=Role.USER, content="旧问题三"),
                Message(
                    role=Role.ASSISTANT,
                    content="旧回答三",
                    usage=Usage(input_tokens=12, output_tokens=1),
                ),
            ],
            summary="历史摘要",
            offset=3,
        )
        agent = TaskAgent(engine, profile, session, save=False)

        list(agent.stream("最新问题"))

        self.assertEqual(agent.session.summary, "历史摘要")
        self.assertEqual(agent.session.offset, 7)
        self.assertEqual(len(engine.requests), 2)
        self.assertEqual(
            [message.content for message in engine.requests[-1].messages],
            ["系统提示词", f"{SUMMARY_PREFIX}\n历史摘要", "最新问题"],
        )

    def test_compaction_does_not_trigger_without_usage(self) -> None:
        engine = FakeEngine()
        profile = Profile(
            name="助手",
            prompt="系统提示词",
            tools=[],
            compaction_threshold=1,
            compaction_turns=1,
        )
        session = Session(
            id="session-8",
            profile="助手",
            name="默认会话",
            messages=[
                Message(role=Role.SYSTEM, content="系统提示词"),
                Message(role=Role.USER, content="旧问题"),
                Message(role=Role.ASSISTANT, content="旧回答"),
            ],
        )
        agent = TaskAgent(engine, profile, session, save=False)

        list(agent.stream("新问题"))

        self.assertEqual(agent.session.summary, "")
        self.assertEqual(agent.session.offset, 1)
        self.assertEqual(len(engine.requests), 1)

    def test_compaction_requires_input_tokens_strictly_above_threshold(self) -> None:
        engine = FakeEngine()
        profile = Profile(
            name="助手",
            prompt="系统提示词",
            tools=[],
            compaction_threshold=10,
            compaction_turns=1,
        )
        session = Session(
            id="session-9",
            profile="助手",
            name="默认会话",
            messages=[
                Message(role=Role.SYSTEM, content="系统提示词"),
                Message(role=Role.USER, content="旧问题"),
                Message(
                    role=Role.ASSISTANT,
                    content="旧回答",
                    usage=Usage(input_tokens=10, output_tokens=1),
                ),
            ],
        )
        agent = TaskAgent(engine, profile, session, save=False)

        list(agent.stream("新问题"))

        self.assertEqual(agent.session.summary, "")
        self.assertEqual(agent.session.offset, 1)
        self.assertEqual(len(engine.requests), 1)

    def test_summary_failure_does_not_modify_session(self) -> None:
        engine = FakeEngine(fail_summary=True)
        profile = Profile(
            name="助手",
            prompt="系统提示词",
            tools=[],
            compaction_threshold=5,
            compaction_turns=1,
        )
        session = Session(
            id="session-4",
            profile="助手",
            name="默认会话",
            messages=[
                Message(role=Role.SYSTEM, content="系统提示词"),
                Message(role=Role.USER, content="旧问题"),
                Message(
                    role=Role.ASSISTANT,
                    content="旧回答",
                    usage=Usage(input_tokens=6, output_tokens=1),
                ),
            ],
        )
        agent = TaskAgent(engine, profile, session, save=False)

        list(agent.stream("新问题"))

        self.assertEqual(agent.session.summary, "")
        self.assertEqual(agent.session.offset, 1)
        self.assertEqual(len(engine.requests), 2)
        self.assertEqual(
            [message.content for message in agent.session.messages],
            ["系统提示词", "旧问题", "旧回答", "新问题", "最终回答"],
        )
        self.assertEqual(engine.requests[-1].messages[1].content, "旧问题")

    def test_summary_text_is_written_back_even_if_prompt_mentions_soft_cap(self) -> None:
        engine = FakeEngine(summary_text="较长历史摘要")
        profile = Profile(
            name="助手",
            prompt="系统提示词",
            tools=[],
            compaction_threshold=5,
            compaction_turns=1,
        )
        session = Session(
            id="session-10",
            profile="助手",
            name="默认会话",
            messages=[
                Message(role=Role.SYSTEM, content="系统提示词"),
                Message(role=Role.USER, content="旧问题"),
                Message(
                    role=Role.ASSISTANT,
                    content="旧回答",
                    usage=Usage(input_tokens=6, output_tokens=1),
                ),
            ],
            summary="已有摘要",
            offset=1,
        )
        agent = TaskAgent(engine, profile, session, save=False)

        list(agent.stream("新问题"))

        self.assertEqual(agent.session.summary, "较长历史摘要")
        self.assertEqual(agent.session.offset, 3)
        self.assertEqual(len(engine.requests), 2)
        self.assertEqual(
            [message.content for message in engine.requests[-1].messages],
            ["系统提示词", f"{SUMMARY_PREFIX}\n较长历史摘要", "新问题"],
        )

    def test_session_roundtrip_preserves_summary_and_offset(self) -> None:
        session = Session(
            id="session-6",
            profile="助手",
            name="默认会话",
            model="",
            messages=[
                Message(role=Role.SYSTEM, content="系统提示词"),
                Message(role=Role.USER, content="旧问题"),
                Message(role=Role.ASSISTANT, content="旧回答"),
                Message(role=Role.USER, content="新问题"),
            ],
            summary="历史摘要",
            offset=3,
        )

        restored = Session.model_validate(session.model_dump())

        self.assertEqual(restored.summary, "历史摘要")
        self.assertEqual(restored.offset, 3)
        self.assertEqual(len(restored.messages), 4)


if __name__ == "__main__":
    unittest.main()
