import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from vnag.agent import TaskAgent
from vnag.constant import AttachmentKind, Role
from vnag.gateways.completion_gateway import CompletionGateway
from vnag.gateways.openrouter_gateway import OpenrouterGateway
from vnag.object import Attachment, Delta, Message, Profile, Request, Session


class FakeEngine:
    def __init__(self) -> None:
        self.last_request: Request | None = None

    def get_skill_catalog(self) -> str:
        return ""

    def get_tool_schemas(self, tools: list[str] | None = None) -> list:
        return []

    def get_skill_schema(self):  # type: ignore[no-untyped-def]
        return None

    def stream(self, request: Request):  # type: ignore[no-untyped-def]
        self.last_request = request
        yield Delta(id="resp-1", content="已处理")


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
                    attachments=[
                        Attachment(
                            kind=AttachmentKind.IMAGE,
                            path="demo.png",
                        )
                    ],
                ),
                Message(role=Role.ASSISTANT, content="已分析图片"),
            ],
        )

        agent = TaskAgent(FakeEngine(), profile, session, save=False)  # type: ignore[arg-type]

        self.assertEqual(agent.round_start, 1)
        self.assertEqual(agent.round_prompt, "")
        self.assertEqual(len(agent.round_attachments), 1)
        self.assertEqual(agent.round_attachments[0].path, "demo.png")

        agent.delete_round()

        self.assertEqual(
            [message.role for message in agent.session.messages],
            [Role.SYSTEM],
        )

    def test_agent_stream_keeps_attachments_for_resend(self) -> None:
        engine = FakeEngine()
        profile = Profile(name="助手", prompt="系统提示词", tools=[])
        session = Session(
            id="session-stream-attachments",
            profile="助手",
            name="默认会话",
            messages=[Message(role=Role.SYSTEM, content="系统提示词")],
        )
        attachments = [
            Attachment(
                kind=AttachmentKind.FILE,
                path="report.pdf",
                name="report.pdf",
                mime="application/pdf",
            )
        ]

        agent = TaskAgent(engine, profile, session, save=False)  # type: ignore[arg-type]

        list(agent.stream("请总结这个文件", attachments=attachments))

        self.assertIsNotNone(engine.last_request)
        assert engine.last_request is not None
        self.assertEqual(engine.last_request.messages[-1].attachments, attachments)
        self.assertEqual(agent.round_prompt, "请总结这个文件")
        self.assertEqual(agent.round_attachments, attachments)
        self.assertEqual(agent.messages[-2].attachments, attachments)

        prompt, resent_attachments = agent.pop_round()

        self.assertEqual(prompt, "请总结这个文件")
        self.assertEqual(resent_attachments, attachments)
        self.assertEqual([message.role for message in agent.messages], [Role.SYSTEM])

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
                    attachments=[
                        Attachment(
                            kind=AttachmentKind.IMAGE,
                            path=str(image_path),
                        )
                    ],
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

    def test_completion_gateway_uses_file_block_for_remote_attachment(self) -> None:
        gateway = CompletionGateway()
        messages = [
            Message(
                role=Role.USER,
                attachments=[
                    Attachment(
                        kind=AttachmentKind.FILE,
                        name="report.pdf",
                        url="https://example.com/report.pdf",
                    )
                ],
            )
        ]

        converted = gateway._convert_messages(messages)

        self.assertEqual(converted[0]["content"][0]["type"], "file")
        self.assertEqual(
            converted[0]["content"][0]["file"]["filename"],
            "report.pdf",
        )
        self.assertEqual(
            converted[0]["content"][0]["file"]["file_data"],
            "https://example.com/report.pdf",
        )

    def test_completion_gateway_reads_local_file_attachment(self) -> None:
        gateway = CompletionGateway()

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir).joinpath("report.pdf")
            file_path.write_bytes(b"%PDF-1.4 fake data")

            messages = [
                Message(
                    role=Role.USER,
                    attachments=[
                        Attachment(
                            kind=AttachmentKind.FILE,
                            path=str(file_path),
                        )
                    ],
                )
            ]

            converted = gateway._convert_messages(messages)

        self.assertEqual(converted[0]["content"][0]["type"], "file")
        self.assertEqual(
            converted[0]["content"][0]["file"]["filename"],
            "report.pdf",
        )
        self.assertTrue(
            converted[0]["content"][0]["file"]["file_data"].startswith(
                "data:application/pdf;base64,"
            )
        )

    def test_openrouter_gateway_reuses_attachment_content_builder(self) -> None:
        gateway = OpenrouterGateway()
        messages = [
            Message(
                role=Role.USER,
                content="分析这些附件",
                attachments=[
                    Attachment(
                        kind=AttachmentKind.IMAGE,
                        url="https://example.com/demo.png",
                    ),
                    Attachment(
                        kind=AttachmentKind.FILE,
                        name="report.pdf",
                        url="https://example.com/report.pdf",
                    ),
                ],
            )
        ]

        converted = gateway._convert_messages(messages)

        self.assertEqual(converted[0]["role"], "user")
        self.assertEqual(converted[0]["content"][0]["type"], "text")
        self.assertEqual(converted[0]["content"][1]["type"], "image_url")
        self.assertEqual(converted[0]["content"][2]["type"], "file")


if __name__ == "__main__":
    unittest.main()
