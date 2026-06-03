"""ModelInfo 与 OpenAI 列表解析单元测试"""

from types import SimpleNamespace

from vnag.gateways.completion_gateway import parse_openai_model


def _model(model_id: str, owned_by: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=model_id, owned_by=owned_by)


def test_parse_openai_model_with_slash() -> None:
    info = parse_openai_model(_model("openai/gpt-4o", "openai"))
    assert info.id == "openai/gpt-4o"
    assert info.provider == "openai"
    assert info.name == "gpt-4o"


def test_parse_openai_model_with_owned_by() -> None:
    info = parse_openai_model(_model("gpt-4o", "openai"))
    assert info.id == "gpt-4o"
    assert info.provider == "openai"
    assert info.name == "gpt-4o"


def test_parse_openai_model_flat() -> None:
    info = parse_openai_model(_model("gpt-4o", ""))
    assert info.id == "gpt-4o"
    assert info.provider == ""
    assert info.name == "gpt-4o"


def test_parse_openai_model_owned_by_none() -> None:
    info = parse_openai_model(_model("openai/gpt-4", None))
    assert info.provider == "openai"
    assert info.name == "gpt-4"
