from __future__ import annotations

from typing import Callable, Dict

from agents.common import ModelRegistry
from . import settings

ModelCaller = Callable[[str, str, object], str]


def build_node_models(model_caller: ModelCaller) -> Dict[str, ModelRegistry]:
    """Return a mapping of node name -> ModelRegistry where each registry's callables
    use the provided `model_caller(model_name, prompt, state)` function.
    """
    return {
        "orchestrator": ModelRegistry(
            intent_model=lambda prompt, state: model_caller(settings.MODEL_INTENT_DETECTION, prompt, state)
        ),
        "code_analyzer": ModelRegistry(
            code_model=lambda prompt, state: model_caller(settings.MODEL_CODE_ANALYZER, prompt, state)
        ),
        "approach_detection": ModelRegistry(
            reasoning_model=lambda prompt, state: model_caller(settings.MODEL_APPROACH_DETECTOR, prompt, state)
        ),
        "approach_validator": ModelRegistry(
            reasoning_model=lambda prompt, state: model_caller(settings.MODEL_APPROACH_VALIDATOR, prompt, state)
        ),
        "hint_agent": ModelRegistry(
            reasoning_model=lambda prompt, state: model_caller(settings.MODEL_HINT_AGENT, prompt, state)
        ),
        "strategy_agent": ModelRegistry(
            reasoning_model=lambda prompt, state: model_caller(settings.MODEL_STRATEGY_AGENT, prompt, state)
        ),
    }
