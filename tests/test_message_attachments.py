import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from vnag.agent import TaskAgent
from vnag.constant import AttachmentKind, Role
from vnag.gateways.completion_gateway import CompletionGateway
from vnag.object import Attachment, Message, Profile, Session


class FakeEngine:
    def get_skill_catalog(self) -> str:
        return ""

    def get_tool_schemas(self, tools: list[str] | None = None) -> list:
        return []

    def get_skill_schema(self):  # type: ignore[no-untyped-def]
        return None


class MessageAttachmentTestCase(unittest.TestCase):
    def test_message_defaults_keep_backward_compatible_shape(self) -> None:
        message = Message.model_validate({
            "role": "user",
            "content": "你好",
        })

        self.assertEqual(message.attachments, [])

    def test_agent_recognizes_attachment_only_round(self) -> None:
        profile = Profile(name="助手", prompt="系统提示词", tools=[])
        session = Session(
            id="session-attachment-round",
            profile="助手",
            name="默认会话",
            messages=[
                Message(role=Role.SYSTEM, content="系统提示词"),
                Message(
                    role=Role.USER,
                    attachments=[Attachment(path="demo.png")],
                ),
                Message(role=Role.ASSISTANT, content="已分析图片"),
            ],
        )

        agent = TaskAgent(FakeEngine(), profile, session, save=False)  # type: ignore[arg-type]

        self.assertEqual(agent.round_start, 1)
        self.assertEqual(agent.round_prompt, "")

        agent.delete_round()

        self.assertEqual(
            [message.role for message in agent.session.messages],
            [Role.SYSTEM],
        )

    def test_completion_gateway_uses_image_url_for_remote_attachment(self) -> None:
        gateway = CompletionGateway()
        messages = [
            Message(
                role=Role.USER,
                content="请描述图片",
                attachments=[
                    Attachment(
                        kind=AttachmentKind.IMAGE,
                        url="https://example.com/demo.png",
                    )
                ],
            )
        ]

        converted = gateway._convert_messages(messages)

        self.assertEqual(converted[0]["role"], "user")
        self.assertEqual(converted[0]["content"][0]["type"], "text")
        self.assertEqual(converted[0]["content"][1]["type"], "image_url")
        self.assertEqual(
            converted[0]["content"][1]["image_url"]["url"],
            "https://example.com/demo.png",
        )

    def test_completion_gateway_reads_local_image_attachment(self) -> None:
        gateway = CompletionGateway()

        with TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir).joinpath("chart.png")
            image_path.write_bytes(b"fake image bytes")

            messages = [
                Message(
                    role=Role.USER,
                    attachments=[Attachment(path=str(image_path))],
                )
            ]

            converted = gateway._convert_messages(messages)

        self.assertEqual(converted[0]["role"], "user")
        self.assertEqual(converted[0]["content"][0]["type"], "image_url")
        self.assertTrue(
            converted[0]["content"][0]["image_url"]["url"].startswith(
                "data:image/png;base64,"
            )
        )

    def test_completion_gateway_rejects_unsupported_attachment_kind(self) -> None:
        gateway = CompletionGateway()
        messages = [
            Message(
                role=Role.USER,
                attachments=[Attachment(kind=AttachmentKind.FILE, path="report.pdf")],
            )
        ]

        with self.assertRaises(ValueError):
            gateway._convert_messages(messages)


if __name__ == "__main__":
    unittest.main()
