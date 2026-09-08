import json
from typing import Any

from runtrail.evaluator.base import BaseEvaluator
from runtrail.gateway.litellm_adapter import LiteLLMAdapter

DEFAULT_PROMPT_TEMPLATE = """You are grading an AI agent's answer.

Task ground truth / rubric: {ground_truth}
Agent's answer: {output}

Respond with ONLY a JSON object, no other text: \
{{"passed": true|false, "score": <0.0-1.0>, "reason": "<short reason>"}}"""


class LLMJudge(BaseEvaluator):
    """Scores Agent output via an LLM-as-judge prompt, routed through LiteLLMAdapter
    (or any object with a compatible `.complete(prompt, **kwargs) -> str`, for
    plugging in a different gateway or a test double).
    """

    def __init__(
        self,
        model: str,
        *,
        rubric: str | None = None,
        prompt_template: str = DEFAULT_PROMPT_TEMPLATE,
        gateway: Any = None,
        **gateway_kwargs: Any,
    ):
        self.model = model
        self.rubric = rubric
        self.prompt_template = prompt_template
        self.gateway = gateway or LiteLLMAdapter(model, **gateway_kwargs)

    def evaluate(self, output: dict, ground_truth: Any) -> dict:
        prompt = self.prompt_template.format(
            ground_truth=self.rubric or ground_truth,
            output=output.get("output"),
        )
        if hasattr(self.gateway, "complete_with_usage"):
            response, tokens = self.gateway.complete_with_usage(prompt)
        else:
            response, tokens = self.gateway.complete(prompt), {}

        try:
            verdict = json.loads(response)
        except json.JSONDecodeError:
            result = {"passed": False, "score": 0.0, "error": f"LLMJudge returned non-JSON: {response!r}"}
            return {**result, "tokens": tokens} if tokens else result

        result = {
            "passed": bool(verdict.get("passed", False)),
            "score": float(verdict.get("score", 0.0)),
            "reason": verdict.get("reason", ""),
        }
        return {**result, "tokens": tokens} if tokens else result
