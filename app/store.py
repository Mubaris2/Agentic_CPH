from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, List
import json

from sqlalchemy import create_engine, String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

from redis.asyncio import Redis


class Base(DeclarativeBase):
    pass


class ChatTurn(Base):
    __tablename__ = "chat_turns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), index=True)
    user_input: Mapped[str] = mapped_column(Text)
    code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_response: Mapped[str] = mapped_column(Text)
    state_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class SessionStore:
    def __init__(self, redis_url: Optional[str], ttl_seconds: int = 86400):
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.client: Optional[Redis] = None
        self._memory: Dict[str, Dict[str, Any]] = {}

    async def connect(self) -> None:
        if not self.redis_url:
            return
        self.client = Redis.from_url(self.redis_url, decode_responses=True)
        await self.client.ping()

    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        if self.client is None:
            return self._memory.get(session_id)
        raw = await self.client.get(f"session:{session_id}")
        if not raw:
            return None
        return json.loads(raw)

    async def set(self, session_id: str, state: Dict[str, Any]) -> None:
        if self.client is None:
            self._memory[session_id] = state
            return
        await self.client.setex(f"session:{session_id}", self.ttl_seconds, json.dumps(state, default=str))


class HistoryStore:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, future=True)

    def init_db(self) -> None:
        Base.metadata.create_all(self.engine)

    def add_turn(
        self,
        session_id: str,
        user_input: str,
        code: Optional[str],
        final_response: str,
        state: Dict[str, Any],
    ) -> None:
        row = ChatTurn(
            session_id=session_id,
            user_input=user_input,
            code=code,
            final_response=final_response,
            state_json=json.dumps(state, default=str),
        )
        with Session(self.engine) as session:
            session.add(row)
            session.commit()

    def get_recent_turns(self, session_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        with Session(self.engine) as session:
            rows = (
                session.query(ChatTurn)
                .filter(ChatTurn.session_id == session_id)
                .order_by(ChatTurn.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "user_input": row.user_input,
                    "code": row.code,
                    "final_response": row.final_response,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
