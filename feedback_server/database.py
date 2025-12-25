from abc import ABC, abstractmethod
from datetime import datetime

from peewee import (
    AutoField,
    CharField,
    DateTimeField,
    Model,
    SqliteDatabase as PeeweeSqliteDatabase,
    TextField,
)


class BaseFeedbackDatabase(ABC):
    """反馈数据库抽象基类"""

    @abstractmethod
    def save_feedback(
        self,
        user_id: str,
        session_id: str,
        session_name: str,
        profile_name: str,
        profile_hash: str,
        model: str,
        rating: str,
        comment: str,
        session_file_path: str,
    ) -> bool:
        """保存反馈"""
        pass

    @abstractmethod
    def load_feedbacks(
        self,
        user_id: str | None = None,
        rating: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> list[dict]:
        """加载反馈"""
        pass


class DbFeedbackSession(Model):
    """反馈记录表"""

    id: AutoField = AutoField()

    user_id: CharField = CharField()
    session_id: CharField = CharField()

    session_name: CharField = CharField()
    profile_name: CharField = CharField()
    profile_hash: CharField = CharField(max_length=64)
    model: CharField = CharField()

    rating: CharField = CharField(default="thumbs_up")
    comment: TextField = TextField(default="")

    session_file_path: CharField = CharField()

    updated_at: DateTimeField = DateTimeField()

    class Meta:
        indexes = ((("user_id", "session_id"), True),)


class SqliteFeedbackDatabase(BaseFeedbackDatabase):
    """SQLite数据库实现"""

    def __init__(self, db_path: str) -> None:
        """初始化数据库"""
        self.db: PeeweeSqliteDatabase = PeeweeSqliteDatabase(db_path)
        DbFeedbackSession._meta.database = self.db
        self.db.connect()
        self.db.create_tables([DbFeedbackSession])

    def save_feedback(
        self,
        user_id: str,
        session_id: str,
        session_name: str,
        profile_name: str,
        profile_hash: str,
        model: str,
        rating: str,
        comment: str,
        session_file_path: str,
    ) -> bool:
        """保存或更新反馈"""
        data: dict = {
            "user_id": user_id,
            "session_id": session_id,
            "session_name": session_name,
            "profile_name": profile_name,
            "profile_hash": profile_hash,
            "model": model,
            "rating": rating,
            "comment": comment,
            "session_file_path": session_file_path,
            "updated_at": datetime.now(),
        }

        DbFeedbackSession.insert(**data).on_conflict_replace().execute()
        return True

    def load_feedbacks(
        self,
        user_id: str | None = None,
        rating: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> list[dict]:
        """加载反馈"""
        query = DbFeedbackSession.select()

        if user_id:
            query = query.where(DbFeedbackSession.user_id == user_id)
        if rating:
            query = query.where(DbFeedbackSession.rating == rating)
        if start_time:
            start_dt: datetime = datetime.fromisoformat(start_time)
            query = query.where(DbFeedbackSession.updated_at >= start_dt)
        if end_time:
            end_dt: datetime = datetime.fromisoformat(end_time)
            query = query.where(DbFeedbackSession.updated_at < end_dt)

        query = query.order_by(DbFeedbackSession.updated_at.desc())

        results: list[dict] = []
        for record in query:
            feedback: dict = {
                "user_id": record.user_id,
                "session_id": record.session_id,
                "session_name": record.session_name,
                "profile_name": record.profile_name,
                "profile_hash": record.profile_hash,
                "model": record.model,
                "rating": record.rating,
                "comment": record.comment,
                "session_file_path": record.session_file_path,
                "updated_at": record.updated_at.isoformat(),
            }
            results.append(feedback)

        return results
