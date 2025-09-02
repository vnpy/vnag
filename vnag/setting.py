from .utility import load_json


# RAG系统默认配置
SETTINGS: dict = {
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": "",
    "model_name": "anthropic/claude-3.7-sonnet",
    "max_tokens": 2000,
    "temperature": 0.7
}

SETTING_FILENAME: str = "gateway_setting.json"
SETTINGS.update(load_json(SETTING_FILENAME))
