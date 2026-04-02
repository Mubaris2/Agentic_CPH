import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class Storage:
    def __init__(self, db_path: str = "db/coach.db") -> None:
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    weaknesses TEXT NOT NULL,
                    topics TEXT NOT NULL,
                    raw_response TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_session(self, score: int, weaknesses: List[str], topics: List[str], raw_response: Dict[str, Any]) -> int:
        created_at = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sessions (created_at, score, weaknesses, topics, raw_response)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    score,
                    json.dumps(weaknesses),
                    json.dumps(topics),
                    json.dumps(raw_response),
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def get_sessions(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, score, weaknesses, topics
                FROM sessions
                ORDER BY id DESC
                """
            ).fetchall()

        sessions = []
        for row in rows:
            sessions.append(
                {
                    "id": row[0],
                    "created_at": row[1],
                    "score": row[2],
                    "weaknesses": json.loads(row[3]),
                    "topics": json.loads(row[4]),
                }
            )
        return sessions
