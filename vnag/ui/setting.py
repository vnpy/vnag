import json
from pathlib import Path

from ..utility import TEMP_DIR


SETTING_FILENAME: str = "ui_setting.json"
SETTING_FILEPATH: Path = TEMP_DIR.joinpath(SETTING_FILENAME)


def load_favorite_models() -> list[str]:
    """加载常用模型"""
    if not SETTING_FILEPATH.exists():
        return []

    with open(SETTING_FILEPATH, encoding="utf-8") as f:
        try:
            data: dict = json.load(f)
            models: list[str] = data.get("favorite_models", [])
            return models
        except json.JSONDecodeError:
            return []


def save_favorite_models(models: list[str]) -> None:
    """保存常用模型"""
    data: dict = {"favorite_models": models}

    with open(SETTING_FILEPATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
