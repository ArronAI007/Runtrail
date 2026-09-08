from typing import Any

from runtrail.evaluator.base import BaseEvaluator


class JSONSchemaEvaluator(BaseEvaluator):
    """Validates the agent's 'output' field against a JSON Schema.

    Requires the 'schema' extra: pip install 'runtrail[schema]'.
    """

    def __init__(self, schema: dict):
        self.schema = schema

    def evaluate(self, output: dict, ground_truth: Any) -> dict:
        try:
            import jsonschema
        except ImportError as exc:
            raise ImportError(
                "JSONSchemaEvaluator requires the 'schema' extra: pip install 'runtrail[schema]'"
            ) from exc

        try:
            jsonschema.validate(instance=output.get("output"), schema=self.schema)
        except jsonschema.ValidationError as exc:
            return {"passed": False, "score": 0.0, "error": exc.message}

        return {"passed": True, "score": 1.0}
