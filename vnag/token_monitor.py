import logging
from typing import Optional

from .setting import SETTINGS
from .utility import load_json, save_json


logger = logging.getLogger(__name__)


class TokenMonitor:
    """Token使用监控服务"""

    def __init__(self) -> None:
        """构造函数"""
        self.max_tokens: int = SETTINGS["token.max_tokens"]
        self.warning_threshold: float = SETTINGS["token.warning_threshold"]
        self.usage_file: str = "token_usage.json"
        
        self.current_usage: int = self._load_usage()
        logger.info(f"Token monitor initialized, current usage: {self.current_usage}")

    def _load_usage(self) -> int:
        """加载Token使用量"""
        usage_data = load_json(self.usage_file)
        if usage_data and isinstance(usage_data, dict):
            return usage_data.get("total_tokens", 0)
        return 0

    def _save_usage(self) -> None:
        """保存Token使用量"""
        usage_data = {
            "total_tokens": self.current_usage,
            "max_tokens": self.max_tokens,
            "warning_threshold": self.warning_threshold
        }
        save_json(self.usage_file, usage_data)

    def track_usage(self, tokens_used: int) -> None:
        """记录Token使用量"""
        self.current_usage += tokens_used
        self._save_usage()
        
        logger.info(f"Token usage updated: +{tokens_used}, total: {self.current_usage}")
        
        if self.check_threshold():
            logger.warning(f"Token usage threshold exceeded: {self.get_usage_percentage():.1f}%")

    def check_threshold(self) -> bool:
        """检查是否达到预警阈值"""
        return self.get_usage_percentage() >= self.warning_threshold

    def get_usage_percentage(self) -> float:
        """获取使用率百分比"""
        if self.max_tokens <= 0:
            return 0.0
        return (self.current_usage / self.max_tokens) * 100

    def get_remaining_tokens(self) -> int:
        """获取剩余Token数量"""
        return max(0, self.max_tokens - self.current_usage)

    def reset_usage(self) -> None:
        """重置使用量"""
        self.current_usage = 0
        self._save_usage()
        logger.info("Token usage reset to 0")

    def get_status_message(self) -> Optional[str]:
        """获取状态消息"""
        percentage = self.get_usage_percentage()
        
        if percentage >= self.warning_threshold:
            return f"⚠️ Token使用量已达 {percentage:.1f}%，请注意"
        elif percentage >= 0.5:
            return f"Token使用量: {percentage:.1f}%"
        
        return None