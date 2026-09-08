import json

from runtrail.evaluator.llm_judge import LLMJudge


class _FakeGateway:
    def __init__(self, response: str):
        self._response = response
        self.last_prompt = None

    def complete(self, prompt: str, **kwargs) -> str:
        self.last_prompt = prompt
        return self._response


def test_evaluate_parses_a_passing_verdict():
    gateway = _FakeGateway(json.dumps({"passed": True, "score": 1.0, "reason": "matches"}))
    judge = LLMJudge("gpt-4", gateway=gateway)

    result = judge.evaluate({"output": "Paris"}, "Paris")

    assert result == {"passed": True, "score": 1.0, "reason": "matches"}
    assert "Paris" in gateway.last_prompt


def test_evaluate_parses_a_failing_verdict():
    gateway = _FakeGateway(json.dumps({"passed": False, "score": 0.2, "reason": "wrong city"}))
    judge = LLMJudge("gpt-4", gateway=gateway)

    result = judge.evaluate({"output": "London"}, "Paris")

    assert result["passed"] is False
    assert result["score"] == 0.2


def test_evaluate_handles_non_json_response_gracefully():
    gateway = _FakeGateway("I think this is correct.")
    judge = LLMJudge("gpt-4", gateway=gateway)

    result = judge.evaluate({"output": "Paris"}, "Paris")

    assert result["passed"] is False
    assert "error" in result


def test_evaluate_uses_rubric_over_ground_truth_when_provided():
    gateway = _FakeGateway(json.dumps({"passed": True, "score": 1.0}))
    judge = LLMJudge("gpt-4", rubric="must mention the Eiffel Tower", gateway=gateway)

    judge.evaluate({"output": "I saw the Eiffel Tower"}, "irrelevant ground truth")

    assert "must mention the Eiffel Tower" in gateway.last_prompt
    assert "irrelevant ground truth" not in gateway.last_prompt


def test_evaluate_end_to_end_through_real_litellm_mock_response():
    judge = LLMJudge(
        "gpt-3.5-turbo",
        mock_response=json.dumps({"passed": True, "score": 1.0, "reason": "ok"}),
    )

    result = judge.evaluate({"output": "4"}, "4")

    assert result["passed"] is True
