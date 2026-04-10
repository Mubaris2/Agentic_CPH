from typing import Callable, Dict, Any, List, Optional
import asyncio

from .models import CPAssistantState


class StateGraph:
    def __init__(self):
        self.nodes: Dict[str, Callable[[CPAssistantState], Any]] = {}
        self.edges: Dict[str, List[str]] = {}
        self.conditional: Dict[str, Callable[[CPAssistantState], str]] = {}

    def add_node(self, name: str, fn: Callable[[CPAssistantState], Any]):
        self.nodes[name] = fn

    def add_edge(self, src: str, dst: str):
        self.edges.setdefault(src, []).append(dst)

    def add_conditional_edges(self, src: str, key_fn: Callable[[CPAssistantState], str], mapping: Dict[str, str]):
        # store a small wrapper that selects destination
        def chooser(state: CPAssistantState) -> str:
            key = key_fn(state)
            return mapping.get(key, mapping.get("general", next(iter(mapping.values()))))

        self.conditional[src] = chooser

    async def run(self, entry: str, state: CPAssistantState) -> CPAssistantState:
        # simple executor: runs nodes according to conditional/edges, supports basic parallel join for strategy/code paths
        cur = entry
        merged = dict(state)
        step_count = 0
        max_steps = 64

        while True:
            step_count += 1
            if step_count > max_steps:
                merged.setdefault("intermediate_steps", [])
                merged["intermediate_steps"].append({
                    "node": "graph_runner",
                    "summary": "max steps reached",
                    "payload": {"max_steps": max_steps},
                })
                break

            if cur == "END":
                break

            fn = self.nodes.get(cur)
            if not fn:
                # jump to first outgoing edge
                outs = self.edges.get(cur, [])
                cur = outs[0] if outs else "END"
                continue

            # execute node (support async)
            out = await fn(merged)

            # merge outputs
            for k, v in out.items():
                if k == "intermediate_steps":
                    merged.setdefault("intermediate_steps", [])
                    merged["intermediate_steps"].extend(v)
                else:
                    merged[k] = v

            # decide next node
            # conditional routing
            if cur in self.conditional:
                nxt = self.conditional[cur](merged)
                cur = nxt
                continue

            outs = self.edges.get(cur, [])
            if not outs:
                # end
                break

            # special-case: if we have a fork where one edge is "strategy_agent" and another is "code_analyzer"
            if set(outs) >= {"strategy_agent", "code_analyzer"}:
                # run both in parallel and then continue to approach_detection/validator join
                tasks = [self.nodes["strategy_agent"](merged), self.nodes["code_analyzer"](merged)]
                results = await asyncio.gather(*tasks)
                for res in results:
                    for k, v in res.items():
                        if k == "intermediate_steps":
                            merged.setdefault("intermediate_steps", []).extend(v)
                        else:
                            merged[k] = v

                # after fork, continue through approach detection/validator path
                cur = "approach_detection"
                continue

            # otherwise go to first
            cur = outs[0]

        return merged
