import os
from collections import Counter
from typing import Any, Dict, List

from db.storage import Storage


class MemoryService:
    def __init__(self) -> None:
        db_path = os.getenv("COACH_DB_PATH", "db/coach.db")
        self.storage = Storage(db_path=db_path)

    async def store_session(self, payload: Dict[str, Any]) -> int:
        score = payload.get("evaluation", {}).get("score", 0)
        weaknesses = payload.get("summary", {}).get("weaknesses", [])
        problem_type = payload.get("pattern", {}).get("problem_type", "General")
        topics = [problem_type]

        return self.storage.save_session(
            score=score,
            weaknesses=weaknesses,
            topics=topics,
            raw_response=payload,
        )

    async def get_progress(self) -> Dict[str, Any]:
        sessions = self.storage.get_sessions()

        if not sessions:
            return {
                "past_scores": [],
                "average_score": 0,
                "insights": ["No sessions yet. Complete your first practice run."],
            }

        scores = [s["score"] for s in sessions]
        average_score = round(sum(scores) / len(scores), 2)

        weakness_counter = Counter()
        topic_counter = Counter()
        for session in sessions:
            weakness_counter.update(session.get("weaknesses", []))
            topic_counter.update(session.get("topics", []))

        top_weaknesses = [w for w, _ in weakness_counter.most_common(3)]
        top_topics = [t for t, _ in topic_counter.most_common(3)]

        trend = "stable"
        if len(scores) >= 2:
            if scores[0] > scores[-1]:
                trend = "improving"
            elif scores[0] < scores[-1]:
                trend = "declining"

        insights: List[str] = [f"Performance trend: {trend}."]
        if top_weaknesses:
            insights.append(f"Frequent weaknesses: {', '.join(top_weaknesses)}")
        if top_topics:
            insights.append(f"Most practiced topics: {', '.join(top_topics)}")

        return {
            "past_scores": [
                {
                    "id": s["id"],
                    "created_at": s["created_at"],
                    "score": s["score"],
                }
                for s in sessions
            ],
            "average_score": average_score,
            "insights": insights,
        }
