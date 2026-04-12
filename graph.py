from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from state import State, default_state
from agents.common import ModelRegistry
from agents.orchestrator import orchestrator_node
from agents.code_analyzer import code_analyzer_node
from agents.approach_detector import approach_detection_node
from agents.approach_validator import approach_validator_node
from agents.hint_agent import hint_agent_node
from agents.strategy_agent import strategy_agent_node
from agents.aggregator import response_aggregator_node


def build_graph(models: ModelRegistry | None = None, node_models: dict[str, ModelRegistry] | None = None):
    builder = StateGraph(State)

    def _models_for(node_name: str) -> ModelRegistry | None:
        if node_models and node_name in node_models:
            return node_models[node_name]
        return models

    builder.add_node("orchestrator", lambda state: orchestrator_node(state, models=_models_for("orchestrator")))
    builder.add_node("code_analyzer", lambda state: code_analyzer_node(state, models=_models_for("code_analyzer")))
    builder.add_node("approach_detection", lambda state: approach_detection_node(state, models=_models_for("approach_detection")))
    builder.add_node("approach_validator", lambda state: approach_validator_node(state, models=_models_for("approach_validator")))
    builder.add_node("hint_agent", lambda state: hint_agent_node(state, models=_models_for("hint_agent")))
    builder.add_node("strategy_agent", lambda state: strategy_agent_node(state, models=_models_for("strategy_agent")))
    builder.add_node("response_aggregator", response_aggregator_node)

    builder.add_edge(START, "orchestrator")

    def route_from_intent(state: State):
        intent = state.get("intent") or "general"
        if intent == "hint":
            return "hint"
        if intent == "strategy":
            return "strategy"
        if intent == "analyze":
            return "analyze"
        return "general"

    builder.add_conditional_edges(
        "orchestrator",
        route_from_intent,
        {
            "hint": "hint_agent",
            "strategy": "strategy_agent",
            "analyze": "code_analyzer",
            "general": "response_aggregator",
        },
    )

    builder.add_edge("hint_agent", "response_aggregator")
    builder.add_edge("strategy_agent", "response_aggregator")

    builder.add_edge("code_analyzer", "approach_detection")
    builder.add_edge("code_analyzer", "strategy_agent")
    builder.add_edge("approach_detection", "approach_validator")
    builder.add_edge("approach_validator", "response_aggregator")

    builder.add_edge("response_aggregator", END)

    return builder.compile()


def run_example() -> State:
    graph = build_graph()
    initial = default_state(
        user_input="Can you analyze my solution? I think it TLEs.",
        code="""def solve(a):\n    ans = 0\n    for i in range(len(a)):\n        for j in range(len(a)):\n            if a[i] < a[j]:\n                ans += 1\n    return ans\n""",
        problem_context={
            "title": "Count Inversions",
            "statement": "Given an array, count pairs i<j with a[i] > a[j].",
            "constraints": "1 <= n <= 2e5",
        },
    )
    out = graph.invoke(initial)
    return out


if __name__ == "__main__":
    result = run_example()
    print(result.get("final_response", ""))
