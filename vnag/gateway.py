from typing import Generator

from openai import OpenAI
from openai.types.chat.chat_completion import ChatCompletion


class AgentGateway:
    """连接大模型API的网关，提供统一接口"""

    def __init__(self) -> None:
        """构造函数"""
        self.client: OpenAI | None = None
        self.model_name: str = ""
        
        # 对话状态（框架独立运行）
        self.chat_history: list[dict[str, str]] = []
        
        # 内部组件（延迟初始化）
        self._rag_service = None
        self._session_manager = None

    def init(
        self,
        base_url: str,
        api_key: str,
        model_name: str
    ) -> None:
        """初始化连接和内部服务组件"""
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

        self.model_name = model_name
        
        # 初始化内部组件
        self._init_components()
        
        # 加载历史会话
        self.load_history()

    def invoke_model(
        self, 
        messages: list[dict[str, str]], 
        use_rag: bool = False, 
        user_files: list[str] | None = None
    ) -> str | None:
        """统一模型调用接口（向后兼容 + 新功能）"""
        if not self.client:
            return None

        # 预处理消息
        processed_messages = self._prepare_messages(messages, use_rag, user_files)

        completion: ChatCompletion = self.client.chat.completions.create(
            model=self.model_name,
            messages=processed_messages       # type: ignore
        )

        return completion.choices[0].message.content

    def invoke_streaming(
        self, 
        messages: list[dict[str, str]], 
        use_rag: bool = False, 
        user_files: list[str] | None = None
    ) -> Generator[str, None, None] | None:
        """统一流式调用接口"""
        if not self.client:
            return None

        # 预处理消息  
        processed_messages = self._prepare_messages(messages, use_rag, user_files)

        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=processed_messages,      # type: ignore
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def send_message(self, message: str, use_rag: bool = True, user_files: list[str] | None = None) -> str | None:
        """发送消息并获取回复（框架核心接口）"""
        if not message.strip():
            return None
            
        # 添加用户消息到历史
        user_message = {"role": "user", "content": message}
        self.chat_history.append(user_message)
        
        # 调用模型获取回复
        content = self.invoke_model(
            messages=self.chat_history,
            use_rag=use_rag,
            user_files=user_files
        )
        
        # 添加助手回复到历史
        if content:
            assistant_message = {"role": "assistant", "content": content}
            self.chat_history.append(assistant_message)
            
        # 保存会话
        self._save_session()
        
        return content

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

    def _save_session(self) -> None:
        """保存会话"""
        if self._session_manager:
            self._session_manager.save_session(self.chat_history)

    def _init_components(self) -> None:
        """初始化内部组件"""
        from .rag_service import RAGService
        from .session_manager import SessionManager
        
        self._rag_service = RAGService(self)
        self._session_manager = SessionManager()

    def _prepare_messages(
        self, 
        messages: list[dict[str, str]], 
        use_rag: bool, 
        user_files: list[str] | None
    ) -> list[dict[str, str]]:
        """内部方法：预处理消息"""
        if not use_rag and not user_files:
            # 纯聊天模式：直接返回原始消息
            return messages
            
        if not self._rag_service:
            # RAG组件未初始化，降级到普通聊天
            return messages
            
        if use_rag:
            # RAG模式：知识库检索 + 用户文件
            return self._rag_service.prepare_rag_messages(messages, user_files)
        else:
            # 文件模式：只处理用户文件
            return self._rag_service.prepare_file_messages(messages, user_files)
