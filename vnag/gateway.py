from collections.abc import Generator

from openai import OpenAI
from openai.types.chat.chat_completion import ChatCompletion
from .utility import load_json

from .rag_service import RAGService
from .session_manager import SessionManager


class AgentGateway:
    """连接大模型API的网关，提供统一接口"""

    def __init__(self) -> None:
        """构造函数"""
        self.client: OpenAI | None = None
        self.model_name: str = ""
        # 直接加载配置
        self.settings: dict = load_json("gateway_setting.json")

        # 对话状态（框架独立运行）
        self.chat_history: list = []

        # 内部组件（延迟初始化）
        self._rag_service: RAGService
        self._session_manager: SessionManager

    def init(self) -> None:
        """初始化连接和内部服务组件"""
        # 从配置获取连接参数
        base_url: str = self.settings.get("base_url", "")
        api_key: str = self.settings.get("api_key", "")
        model_name: str = self.settings.get("model_name", "")

        if not base_url or not api_key or not model_name:
            print("配置不完整，请检查以下配置项：")
            if not base_url:
                print("  - base_url: API地址未设置")
            if not api_key:
                print("  - api_key: API密钥未设置")
            if not model_name:
                print("  - model_name: 模型名称未设置")
            return

        self.model_name = model_name

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

        # 初始化内部组件
        self._rag_service = RAGService()
        self._session_manager = SessionManager()

        # 加载历史会话
        self.load_history()

    def invoke_streaming(
        self,
        messages: list[dict[str, str]],
        use_rag: bool = False,
        user_files: list[str] | None = None
    ) -> Generator[str, None, None]:
        """统一流式调用接口"""
        if not self.client:
            yield "LLM客户端未初始化，请检查配置"
            return

        if not self.model_name:
            yield "模型名称未设置，请检查配置"
            return

        # 预处理消息
        processed_messages: list = self._prepare_messages(
            messages,
            use_rag,
            user_files,
        )

        # 确保消息不为空
        if not processed_messages or len(processed_messages) == 0:
            yield "消息处理失败，请检查输入内容"
            return

        # 仅检查消息不为空，具体内容由上层保证

        # 使用关键字参数调用，确保类型匹配
        kwargs: dict[str, object] = {"stream": True}
        if self.settings.get("max_tokens"):
            kwargs["max_tokens"] = int(self.settings["max_tokens"])
        if self.settings.get("temperature"):
            kwargs["temperature"] = float(self.settings["temperature"])

        try:
            stream: ChatCompletion = self.client.chat.completions.create(
                model=self.model_name,
                messages=processed_messages,
                **kwargs,    # type: ignore
            )

            # 流式输出处理
            for chunk in stream:
                # 只处理内容部分（显式检查 None）
                if chunk.choices[0].delta.content is not None:  # type: ignore[attr-defined]
                    yield chunk.choices[0].delta.content        # type: ignore[attr-defined]

        except Exception as e:
            yield f"请求错误: {str(e)}"
            return

    def send_message(
        self,
        message: str,
        use_rag: bool = True,
        user_files: list[str] | None = None
    ) -> Generator[str, None, None]:
        """封装的对话入口：处理历史追加、流式更新与保存。

        Args:
            message: 用户输入文本
            use_rag: 是否启用 RAG 检索
            user_files: 用户临时附加文件路径列表

        Yields:
            模型输出的增量文本片段
        """
        if not message.strip():
            return

        # 追加用户消息
        user_message: dict = {"role": "user", "content": message}
        self.chat_history.append(user_message)

        # 先放入一个空的 assistant，用于逐步累积内容
        assistant_message: dict = {"role": "assistant", "content": ""}
        self.chat_history.append(assistant_message)

        # 透传到底层流式接口，并在产生片段时更新历史中最后一条 assistant 的内容
        for chunk in self.invoke_streaming(
            messages=self.chat_history,
            use_rag=use_rag,
            user_files=user_files,
        ):
            if self.chat_history and self.chat_history[-1]["role"] == "assistant":
                self.chat_history[-1]["content"] += chunk
            yield chunk

        # 结束后保存会话
        self._save_session()

    def get_chat_history(self) -> list[dict[str, str]]:
        """获取当前对话历史"""
        return self.chat_history.copy()

    def clear_history(self) -> None:
        """清空对话历史"""
        self.chat_history.clear()
        self._save_session()

    def load_history(self) -> None:
        """加载对话历史"""
        if self._session_manager:
            self.chat_history = self._session_manager.load_session()

    def new_session(self) -> str:
        """创建新会话"""
        if self._session_manager:
            session_id: str = self._session_manager.create_session()
            self.chat_history.clear()
            return session_id
        return ""

    def get_all_sessions(self) -> list[dict]:
        """获取所有会话"""
        if self._session_manager:
            return self._session_manager.get_all_sessions()
        return []

    def switch_session(self, session_id: str) -> bool:
        """切换会话"""
        if self._session_manager:
            success: bool = self._session_manager.switch_session(session_id)
            if success:
                self.load_history()
            return success
        return False

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if self._session_manager:
            return self._session_manager.delete_session(session_id)
        return False

    def export_session(self, session_id: str | None = None) -> tuple:
        """导出会话
        返回：(会话标题, 会话历史记录)
        """
        if self._session_manager:
            return self._session_manager.export_session(session_id)
        return ("未知会话", [])

    def get_deleted_sessions(self) -> list[dict]:
        """获取所有已删除的会话"""
        if self._session_manager:
            return self._session_manager.get_deleted_sessions()
        return []

    def restore_session(self, session_id: str) -> bool:
        """恢复已删除的会话
        Returns:
            是否成功恢复
        """
        if self._session_manager:
            return self._session_manager.restore_session(session_id)
        return False

    def cleanup_deleted_sessions(self, force_all: bool = False) -> int:
        """清理已删除的会话
        Args:
            force_all: 是否强制清理所有已删除的会话（忽略30天限制）

        Returns:
            清理的会话数量
        """
        if self._session_manager:
            return self._session_manager.cleanup_deleted_sessions(force_all)
        return 0

    def _save_session(self) -> None:
        """保存会话"""
        if self._session_manager:
            self._session_manager.save_session(self.chat_history)

    def _prepare_messages(
        self,
        messages: list[dict[str, str]],
        use_rag: bool,
        user_files: list[str] | None
    ) -> list[dict[str, str]]:
        """内部方法：预处理消息"""
        if use_rag:
            # RAG模式：知识库检索 + 用户文件
            return self._rag_service.prepare_rag_messages(messages, user_files)
        # 非RAG统一走CHAT模板；若有用户文件，会在模板后追加参考内容
        return self._rag_service.prepare_chat_messages(messages, user_files)
