import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from tinydb import TinyDB, Query

from .utility import get_file_path


logger = logging.getLogger(__name__)


class SessionManager:
    """会话管理器（gateway内部组件）"""

    def __init__(self) -> None:
        """构造函数"""
        self.db_path = get_file_path("chat_sessions.json")
        self.db = TinyDB(str(self.db_path))
        self.sessions_table = self.db.table('sessions')
        self.messages_table = self.db.table('messages')
        self.current_session_id: Optional[str] = None
        
        logger.info(f"Session manager initialized with database: {self.db_path}")
        
        # 自动加载或创建默认会话
        self._ensure_current_session()

    def create_session(self, title: str = "新会话") -> str:
        """创建新会话"""
        session_id = str(uuid4())
        session_data = {
            'id': session_id,
            'title': title,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'deleted': False
        }
        
        self.sessions_table.insert(session_data)
        self.current_session_id = session_id
        
        logger.info(f"Created new session: {session_id} - {title}")
        return session_id

    def get_current_session_id(self) -> str:
        """获取或创建当前会话ID"""
        if not self.current_session_id:
            self.current_session_id = self.create_session()
        return self.current_session_id

    def add_message(self, role: str, content: str) -> None:
        """添加消息到当前会话"""
        session_id = self.get_current_session_id()
        
        message_data = {
            'session_id': session_id,
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        
        self.messages_table.insert(message_data)
        
        # 更新会话的最后更新时间
        Session = Query()
        self.sessions_table.update({
            'updated_at': datetime.now().isoformat()
        }, Session.id == session_id)

    def get_current_history(self) -> list[dict[str, str]]:
        """获取当前会话的历史消息"""
        if not self.current_session_id:
            return []
        
        messages = self.messages_table.search(Query().session_id == self.current_session_id)
        messages.sort(key=lambda x: x['timestamp'])
        
        return [{'role': msg['role'], 'content': msg['content']} for msg in messages]

    def get_all_sessions(self) -> list[dict]:
        """获取所有未删除的会话"""
        sessions = self.sessions_table.search(Query().deleted == False)
        return sorted(sessions, key=lambda x: x['updated_at'], reverse=True)

    def switch_session(self, session_id: str) -> bool:
        """切换到指定会话"""
        Session = Query()
        session = self.sessions_table.get(Session.id == session_id)
        
        if session and not session.get('deleted', False):
            self.current_session_id = session_id
            logger.info(f"Switched to session: {session_id}")
            return True
        
        return False

    def update_session_title(self, session_id: str, title: str) -> bool:
        """更新会话标题"""
        Session = Query()
        result = self.sessions_table.update({
            'title': title,
            'updated_at': datetime.now().isoformat()
        }, Session.id == session_id)
        
        return len(result) > 0

    def delete_session(self, session_id: str) -> bool:
        """软删除会话"""
        Session = Query()
        result = self.sessions_table.update({
            'deleted': True,
            'updated_at': datetime.now().isoformat()
        }, Session.id == session_id)
        
        if len(result) > 0 and session_id == self.current_session_id:
            self.current_session_id = None
            
        return len(result) > 0

    def clear_current_session(self) -> None:
        """清空当前会话"""
        if self.current_session_id:
            Message = Query()
            self.messages_table.remove(Message.session_id == self.current_session_id)
            logger.info(f"Cleared current session: {self.current_session_id}")

    def new_session(self) -> str:
        """创建新会话并切换"""
        return self.create_session()
        
    def save_session(self, chat_history: list[dict[str, str]]) -> None:
        """保存会话历史（gateway接口）"""
        if not chat_history:
            return
            
        session_id = self.get_current_session_id()
        
        # 清空当前会话的消息
        Message = Query()
        self.messages_table.remove(Message.session_id == session_id)
        
        # 保存新的消息历史
        for message in chat_history:
            message_data = {
                'session_id': session_id,
                'role': message['role'],
                'content': message['content'],
                'timestamp': datetime.now().isoformat()
            }
            self.messages_table.insert(message_data)
        
        # 更新会话时间戳
        Session = Query()
        self.sessions_table.update({
            'updated_at': datetime.now().isoformat()
        }, Session.id == session_id)
        
        logger.info(f"Session saved with {len(chat_history)} messages")
        
    def load_session(self, session_id: str | None = None) -> list[dict[str, str]]:
        """加载会话历史（gateway接口）"""
        target_session_id = session_id or self.get_current_session_id()
        
        messages = self.messages_table.search(Query().session_id == target_session_id)
        messages.sort(key=lambda x: x['timestamp'])
        
        chat_history = [{'role': msg['role'], 'content': msg['content']} for msg in messages]
        
        logger.info(f"Session loaded with {len(chat_history)} messages")
        return chat_history
        
    def _ensure_current_session(self) -> None:
        """确保有当前会话"""
        if not self.current_session_id:
            # 尝试获取最近的会话
            sessions = self.get_all_sessions()
            if sessions:
                self.current_session_id = sessions[0]['id']
            else:
                # 创建默认会话
                self.current_session_id = self.create_session("默认会话")