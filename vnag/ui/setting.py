import json
from pathlib import Path
from typing import Any, cast

from ..utility import TEMP_DIR


SETTING_FILENAME: str = "ui_setting.json"
SETTING_FILEPATH: Path = TEMP_DIR.joinpath(SETTING_FILENAME)


def _load_settings() -> dict[str, Any]:
    """加载所有设置"""
    if not SETTING_FILEPATH.exists():
        return {}

    try:
        with open(SETTING_FILEPATH, encoding="utf-8") as f:
            return cast(dict[str, Any], json.load(f))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_settings(data: dict[str, Any]) -> None:
    """保存所有设置"""
    with open(SETTING_FILEPATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_setting(key: str, default: Any = None) -> Any:
    """获取配置项

    Args:
        key: 配置键名
        default: 默认值

    Returns:
        配置值或默认值
    """
    settings = _load_settings()
    return settings.get(key, default)


def set_setting(key: str, value: Any) -> None:
    """设置配置项

    Args:
        key: 配置键名
        value: 配置值
    """
    settings = _load_settings()
    settings[key] = value
    _save_settings(settings)


def load_favorite_models() -> list[str]:
    """加载常用模型"""
    return cast(list[str], get_setting("favorite_models", []))


def save_favorite_models(models: list[str]) -> None:
    """保存常用模型"""
    set_setting("favorite_models", models)


def load_zoom_factor() -> float:
    """加载页面缩放倍数"""
    return cast(float, get_setting("zoom_factor", 1.0))


def save_zoom_factor(zoom_factor: float) -> None:
    """保存页面缩放倍数"""
    set_setting("zoom_factor", zoom_factor)


def load_font_family() -> str:
    """加载字体名称"""
    return cast(str, get_setting("font_family", "微软雅黑"))


def save_font_family(font_family: str) -> None:
    """保存字体名称"""
    set_setting("font_family", font_family)


def load_font_size() -> int:
    """加载字体大小"""
    return cast(int, get_setting("font_size", 16))


def save_font_size(font_size: int) -> None:
    """保存字体大小"""
    set_setting("font_size", font_size)


def load_gateway_type() -> str:
    """加载当前选择的 gateway 类型"""
    return cast(str, get_setting("gateway_type", "OpenAI"))


def save_gateway_type(gateway_type: str) -> None:
    """保存当前选择的 gateway 类型"""
    set_setting("gateway_type", gateway_type)


def load_embedder_type() -> str:
    """加载当前选择的 embedder 类型"""
    return cast(str, get_setting("embedder_type", "OpenAI"))


def save_embedder_type(embedder_type: str) -> None:
    """保存当前选择的 embedder 类型"""
    set_setting("embedder_type", embedder_type)