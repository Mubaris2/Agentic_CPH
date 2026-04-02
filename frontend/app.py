import os
from typing import Any, Dict

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Agentic CP Coach", layout="wide")
st.title("Agentic Competitive Programming Coach")

page = st.sidebar.radio("Navigation", ["Practice Mode", "Progress Dashboard"])


def post_analyze(payload: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.post(f"{BACKEND_URL}/analyze", json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def get_progress() -> Dict[str, Any]:
    response = requests.get(f"{BACKEND_URL}/progress", timeout=30)
    response.raise_for_status()
    return response.json()


if page == "Practice Mode":
    st.subheader("Practice Mode")
    code = st.text_area("Paste your code", height=320)
    problem_description = st.text_area("Problem description (optional)", height=120)
    is_correct = st.toggle("My current solution is correct", value=False)
    used_hints = st.toggle("I used hints while solving", value=False)

    if st.button("Analyze", type="primary"):
        if not code.strip():
            st.warning("Code is required.")
        else:
            with st.spinner("Running multi-agent analysis..."):
                try:
                    payload = {
                        "code": code,
                        "problem_description": problem_description,
                        "is_correct": is_correct,
                        "used_hints": used_hints,
                    }
                    result = post_analyze(payload)

                    st.markdown("### Issues")
                    st.write(result["code_analysis"]["detected_issues"])

                    st.markdown("### Possible Bugs")
                    st.write(result["code_analysis"]["possible_bugs"])

                    st.markdown("### Edge Cases Missed")
                    st.write(result["code_analysis"]["edge_cases_missed"])

                    st.markdown("### Complexity")
                    st.write(result["complexity"]) 

                    st.markdown("### Alternative Approaches")
                    st.write(result["strategy"]["alternative_approaches"])

                    st.markdown("### Progressive Hints")
                    st.write(result["hints"]["progressive_hints"])

                    st.markdown("### Thinking Feedback")
                    st.info(result["thinking"]["thinking_feedback"])

                    st.markdown("### Score")
                    st.metric("Session Score", result["evaluation"]["score"])
                    st.write(result["evaluation"]["score_breakdown"])

                    st.markdown("### Summary")
                    st.write(result["summary"])
                except Exception as exc:
                    st.error(f"Failed to analyze: {exc}")

elif page == "Progress Dashboard":
    st.subheader("Progress Dashboard")
    if st.button("Refresh Progress", type="primary"):
        try:
            progress_data = get_progress()
            st.metric("Average Score", progress_data["average_score"])

            scores = [item["score"] for item in progress_data["past_scores"]]
            if scores:
                st.line_chart(scores)

            st.markdown("### Past Scores")
            st.write(progress_data["past_scores"])

            st.markdown("### Insights")
            st.write(progress_data["insights"])
        except Exception as exc:
            st.error(f"Failed to fetch progress: {exc}")
