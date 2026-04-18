import unittest
from typing import Any

from vnag.constant import Role
from vnag.gateways.completion_gateway import CompletionGateway
from vnag.object import Message


class MultimodalGatewayTestCase(unittest.TestCase):
    def test_completion_gateway_passes_through_multimodal_user_content(self) -> None:
        parts: list[dict[str, Any]] = [
            {"type": "text", "text": "page 1"},
            {
                "type": "image_url",
                "image_url": {"url": "data:image/png;base64,xxx"},
            },
        ]

        gateway = CompletionGateway()
        messages = gateway._convert_messages([
            Message(role=Role.USER, content=parts),
        ])

        self.assertEqual(messages[0]["content"], parts)


if __name__ == "__main__":
    unittest.main()
