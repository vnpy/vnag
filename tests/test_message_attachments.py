import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from vnag.agent import TaskAgent
from vnag.constant import AttachmentKind, Role
from vnag.gateways.completion_gateway import CompletionGateway
from vnag.gateways.litellm_gateway import LitellmGateway
from vnag.gateways.openrouter_gateway import OpenrouterGateway
from vnag.gateways.openai_gateway import OpenaiGateway
from vnag.gateways.anthropic_gateway import AnthropicGateway
from vnag.gateways.gemini_gateway import GeminiGateway
from vnag.gateways.bedrock_gateway import BedrockGateway
from vnag.gateways.ollama_gateway import OllamaGateway
from vnag.gateways.dashscope_gateway import DashscopeGateway
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

    def test_completion_gateway_supports_attachment_only_user_message(self) -> None:
        gateway = CompletionGateway()
        messages = [
            Message(
                role=Role.USER,
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
        self.assertEqual(len(converted[0]["content"]), 1)
        self.assertEqual(converted[0]["content"][0]["type"], "image_url")

    def test_completion_gateway_rejects_non_user_attachments(self) -> None:
        gateway = CompletionGateway()
        messages = [
            Message(
                role=Role.ASSISTANT,
                attachments=[
                    Attachment(
                        kind=AttachmentKind.IMAGE,
                        url="https://example.com/demo.png",
                    )
                ],
            )
        ]

        with self.assertRaises(ValueError):
            gateway._convert_messages(messages)

    def test_completion_gateway_rejects_attachment_with_both_url_and_path(self) -> None:
        gateway = CompletionGateway()
        messages = [
            Message(
                role=Role.USER,
                attachments=[
                    Attachment(
                        kind=AttachmentKind.IMAGE,
                        url="https://example.com/demo.png",
                        path="demo.png",
                    )
                ],
            )
        ]

        with self.assertRaises(ValueError):
            gateway._convert_messages(messages)

    def test_completion_gateway_rejects_attachment_without_source(self) -> None:
        gateway = CompletionGateway()
        messages = [
            Message(
                role=Role.USER,
                attachments=[Attachment(kind=AttachmentKind.FILE)],
            )
        ]

        with self.assertRaises(ValueError):
            gateway._convert_messages(messages)

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

    def test_litellm_gateway_reuses_attachment_content_builder(self) -> None:
        gateway = LitellmGateway()
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

    def test_openai_gateway_builds_responses_api_multimodal_content(self) -> None:
        gateway = OpenaiGateway()
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

        converted, instructions = gateway._convert_input(messages)

        self.assertIsNone(instructions)
        self.assertEqual(converted[0]["role"], "user")
        self.assertEqual(converted[0]["content"][0]["type"], "input_text")
        self.assertEqual(converted[0]["content"][1]["type"], "input_image")
        self.assertEqual(converted[0]["content"][2]["type"], "input_file")

    def test_anthropic_gateway_builds_multimodal_user_blocks(self) -> None:
        gateway = AnthropicGateway()

        with TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir).joinpath("chart.png")
            image_path.write_bytes(b"fake image bytes")
            file_path = Path(temp_dir).joinpath("report.pdf")
            file_path.write_bytes(b"%PDF-1.4 fake data")

            messages = [
                Message(
                    role=Role.USER,
                    content="请分析这些附件",
                    attachments=[
                        Attachment(
                            kind=AttachmentKind.IMAGE,
                            path=str(image_path),
                        ),
                        Attachment(
                            kind=AttachmentKind.FILE,
                            path=str(file_path),
                        ),
                    ],
                )
            ]

            _, converted = gateway._convert_messages(messages)

        self.assertEqual(converted[0]["role"], "user")
        self.assertEqual(converted[0]["content"][0]["type"], "text")
        self.assertEqual(converted[0]["content"][1]["type"], "image")
        self.assertEqual(converted[0]["content"][2]["type"], "document")

    def test_gemini_gateway_builds_multimodal_user_parts(self) -> None:
        gateway = GeminiGateway()

        with TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir).joinpath("chart.png")
            image_path.write_bytes(b"fake image bytes")
            file_path = Path(temp_dir).joinpath("report.pdf")
            file_path.write_bytes(b"%PDF-1.4 fake data")

            messages = [
                Message(
                    role=Role.USER,
                    content="请分析这些附件",
                    attachments=[
                        Attachment(
                            kind=AttachmentKind.IMAGE,
                            path=str(image_path),
                        ),
                        Attachment(
                            kind=AttachmentKind.FILE,
                            path=str(file_path),
                        ),
                    ],
                )
            ]

            _, converted = gateway._convert_messages(messages)

        parts = converted[0].parts
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[0].text, "请分析这些附件")
        self.assertEqual(parts[1].inline_data.mime_type, "image/png")
        self.assertEqual(parts[2].inline_data.mime_type, "application/pdf")

    def test_bedrock_gateway_builds_multimodal_user_content(self) -> None:
        gateway = BedrockGateway()

        with TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir).joinpath("chart.png")
            image_path.write_bytes(b"fake image bytes")
            file_path = Path(temp_dir).joinpath("report.pdf")
            file_path.write_bytes(b"%PDF-1.4 fake data")

            messages = [
                Message(
                    role=Role.USER,
                    attachments=[
                        Attachment(
                            kind=AttachmentKind.IMAGE,
                            path=str(image_path),
                        ),
                        Attachment(
                            kind=AttachmentKind.FILE,
                            path=str(file_path),
                        ),
                    ],
                )
            ]

            _, converted = gateway._convert_messages(messages)

        self.assertEqual(converted[0]["role"], "user")
        self.assertEqual(converted[0]["content"][0]["text"], "请分析该文档。")
        self.assertIn("image", converted[0]["content"][1])
        self.assertIn("document", converted[0]["content"][2])

    def test_ollama_gateway_keeps_attachment_only_image_message(self) -> None:
        gateway = OllamaGateway()

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
        self.assertEqual(converted[0]["content"], "")
        self.assertEqual(converted[0]["images"], [str(image_path)])

    def test_ollama_gateway_rejects_file_attachment(self) -> None:
        gateway = OllamaGateway()
        messages = [
            Message(
                role=Role.USER,
                attachments=[
                    Attachment(
                        kind=AttachmentKind.FILE,
                        path="report.pdf",
                    )
                ],
            )
        ]

        with self.assertRaises(ValueError):
            gateway._convert_messages(messages)

    def test_dashscope_gateway_builds_multimodal_user_content(self) -> None:
        gateway = DashscopeGateway()

        with TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir).joinpath("chart.png")
            image_path.write_bytes(b"fake image bytes")

            messages = [
                Message(role=Role.SYSTEM, content="系统提示词"),
                Message(
                    role=Role.USER,
                    content="请描述图片",
                    attachments=[
                        Attachment(
                            kind=AttachmentKind.IMAGE,
                            path=str(image_path),
                        )
                    ],
                ),
                Message(role=Role.ASSISTANT, content="好的"),
            ]

            converted = gateway._convert_multimodal_messages(messages)

        self.assertEqual(converted[0]["role"], "system")
        self.assertEqual(converted[0]["content"][0]["text"], "系统提示词")
        self.assertEqual(converted[1]["role"], "user")
        self.assertEqual(converted[1]["content"][0]["text"], "请描述图片")
        self.assertTrue(converted[1]["content"][1]["image"].startswith("file:///"))
        self.assertEqual(converted[2]["role"], "assistant")
        self.assertEqual(converted[2]["content"][0]["text"], "好的")

    def test_dashscope_gateway_prefers_multimodal_api_when_attachments_exist(self) -> None:
        gateway = DashscopeGateway()
        messages = [
            Message(
                role=Role.USER,
                attachments=[
                    Attachment(
                        kind=AttachmentKind.IMAGE,
                        url="https://example.com/demo.png",
                    )
                ],
            )
        ]

        self.assertTrue(gateway._use_multimodal_api(messages))

    def test_dashscope_gateway_rejects_non_image_attachment(self) -> None:
        gateway = DashscopeGateway()
        messages = [
            Message(
                role=Role.USER,
                attachments=[
                    Attachment(
                        kind=AttachmentKind.FILE,
                        path="report.pdf",
                    )
                ],
            )
        ]

        with self.assertRaises(ValueError):
            gateway._convert_multimodal_messages(messages)


if __name__ == "__main__":
    unittest.main()
