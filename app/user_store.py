"""user_store.py

Manages multi-user profiles stored in the same SQLite database used by the
rest of the app.  Each user has:
  - username  (unique)
  - strengths / weaknesses (free-text, comma-separated tags)
  - stats     (JSON blob: problems_solved, rating_estimate, etc.)
  - created_at / updated_at

A separate `SolvedProblem` table records each problem a user has solved so
the sidebar can show a personal history list.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    create_engine,
    String,
    Text,
    DateTime,
    Integer,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, relationship


# ---------------------------------------------------------------------------
# ORM models
# ---------------------------------------------------------------------------


class _Base(DeclarativeBase):
    pass


class User(_Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    strengths: Mapped[str] = mapped_column(Text, default="")   # comma-separated
    weaknesses: Mapped[str] = mapped_column(Text, default="")  # comma-separated
    stats_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    solved_problems: Mapped[List["SolvedProblem"]] = relationship(
        "SolvedProblem", back_populates="user", cascade="all, delete-orphan"
    )


class SolvedProblem(_Base):
    __tablename__ = "solved_problems"
    __table_args__ = (UniqueConstraint("user_id", "problem_id", name="uq_user_problem"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    problem_id: Mapped[str] = mapped_column(String(120))   # e.g. "1234_A"
    title: Mapped[str] = mapped_column(Text, default="")
    platform: Mapped[str] = mapped_column(String(40), default="codeforces")
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tags: Mapped[str] = mapped_column(Text, default="")    # JSON array string
    solved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped["User"] = relationship("User", back_populates="solved_problems")


# ---------------------------------------------------------------------------
# Store class
# ---------------------------------------------------------------------------


def _user_to_dict(user: User) -> Dict[str, Any]:
    stats = {}
    try:
        stats = json.loads(user.stats_json or "{}")
    except Exception:
        pass
    return {
        "id": user.id,
        "username": user.username,
        "strengths": [s.strip() for s in user.strengths.split(",") if s.strip()],
        "weaknesses": [w.strip() for w in user.weaknesses.split(",") if w.strip()],
        "stats": stats,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


def _solved_to_dict(sp: SolvedProblem) -> Dict[str, Any]:
    tags = []
    try:
        tags = json.loads(sp.tags or "[]")
    except Exception:
        pass
    return {
        "id": sp.id,
        "problem_id": sp.problem_id,
        "title": sp.title,
        "platform": sp.platform,
        "rating": sp.rating,
        "tags": tags,
        "solved_at": sp.solved_at.isoformat(),
    }


class UserStore:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, future=True)

    def init_db(self) -> None:
        _Base.metadata.create_all(self.engine)

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def create_user(self, username: str) -> Dict[str, Any]:
        with Session(self.engine) as session:
            user = User(username=username)
            session.add(user)
            session.commit()
            session.refresh(user)
            return _user_to_dict(user)

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            return _user_to_dict(user) if user else None

    def get_user_by_name(self, username: str) -> Optional[Dict[str, Any]]:
        with Session(self.engine) as session:
            user = session.query(User).filter(User.username == username).first()
            return _user_to_dict(user) if user else None

    def list_users(self) -> List[Dict[str, Any]]:
        with Session(self.engine) as session:
            return [_user_to_dict(u) for u in session.query(User).order_by(User.created_at).all()]

    def update_user(
        self,
        user_id: int,
        *,
        username: Optional[str] = None,
        strengths: Optional[List[str]] = None,
        weaknesses: Optional[List[str]] = None,
        stats: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            if not user:
                return None
            if username is not None:
                user.username = username
            if strengths is not None:
                user.strengths = ", ".join(strengths)
            if weaknesses is not None:
                user.weaknesses = ", ".join(weaknesses)
            if stats is not None:
                existing: Dict[str, Any] = {}
                try:
                    existing = json.loads(user.stats_json or "{}")
                except Exception:
                    pass
                existing.update(stats)
                user.stats_json = json.dumps(existing)
            user.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(user)
            return _user_to_dict(user)

    def delete_user(self, user_id: int) -> bool:
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            if not user:
                return False
            session.delete(user)
            session.commit()
            return True

    # ------------------------------------------------------------------
    # Solved problems
    # ------------------------------------------------------------------

    def add_solved_problem(
        self,
        user_id: int,
        problem_id: str,
        title: str = "",
        platform: str = "codeforces",
        rating: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        with Session(self.engine) as session:
            # upsert: if already exists, update solved_at
            existing = (
                session.query(SolvedProblem)
                .filter(SolvedProblem.user_id == user_id, SolvedProblem.problem_id == problem_id)
                .first()
            )
            if existing:
                existing.solved_at = datetime.utcnow()
                existing.title = title or existing.title
                session.commit()
                session.refresh(existing)
                return _solved_to_dict(existing)

            sp = SolvedProblem(
                user_id=user_id,
                problem_id=problem_id,
                title=title,
                platform=platform,
                rating=rating,
                tags=json.dumps(tags or []),
            )
            session.add(sp)
            # bump stats counter
            user = session.get(User, user_id)
            if user:
                stats: Dict[str, Any] = {}
                try:
                    stats = json.loads(user.stats_json or "{}")
                except Exception:
                    pass
                stats["problems_solved"] = stats.get("problems_solved", 0) + 1
                user.stats_json = json.dumps(stats)
                user.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(sp)
            return _solved_to_dict(sp)

    def get_solved_problems(
        self, user_id: int, limit: int = 50
    ) -> List[Dict[str, Any]]:
        with Session(self.engine) as session:
            rows = (
                session.query(SolvedProblem)
                .filter(SolvedProblem.user_id == user_id)
                .order_by(SolvedProblem.solved_at.desc())
                .limit(limit)
                .all()
            )
            return [_solved_to_dict(r) for r in rows]
