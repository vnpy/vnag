"""运行脚本：测试 AnthropicGateway

用法：
  python scripts/run_anthropic.py <prompt>
说明：
  - 从 gateway_setting.json 读取 base_url/api_key/model_name/max_tokens
  - 提示词从命令行第1个参数读取
"""

from __future__ import annotations

import sys
from collections.abc import Iterable

from vnag.anthropic_gateway import AnthropicGateway
from vnag.utility import load_json


def main() -> None:
    prompt: str = sys.argv[1]

    settings = load_json("gateway_setting.json")
    base_url: str = settings.pop("base_url")
    api_key: str = settings.pop("api_key")
    model_name: str = settings.pop("model_name")
    max_tokens: int = settings.pop("max_tokens")    # max_tokens必传

    gateway = AnthropicGateway()
    gateway.init(base_url=base_url, api_key=api_key)

    messages: list[dict[str, str]] = [
        {"role": "user", "content": prompt},
    ]

    stream: Iterable[str] = gateway.invoke_streaming(
        messages=messages,
        model_name=model_name,
        max_tokens=max_tokens,
        **settings
    )

    for chunk in stream:
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    main()


