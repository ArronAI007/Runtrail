from enum import Enum


class FailureCategory(str, Enum):
    HALLUCINATION = "hallucination"
    TOOL_CALL_ERROR = "tool_call_error"
    PROMPT_DEFECT = "prompt_defect"
    TOOL_RESPONSE_ERROR = "tool_response_error"
    CONTEXT_OVERFLOW = "context_overflow"
    INFINITE_LOOP = "infinite_loop"
    PLANNING_ERROR = "planning_error"
    UNKNOWN = "unknown"


class FailureClassifier:
    """Heuristically classifies a failed case using signals already present in
    the Trace: the exception type/message TaskRunner caught, and any
    evaluator-reported 'error' or 'tool_call_accuracy'.

    This is pattern matching, not semantic understanding — it can't reach
    HALLUCINATION or PLANNING_ERROR, which need an LLM judge (LLMJudge is not
    implemented yet) to assess *why* an otherwise-successful run was wrong.
    """

    def classify(self, output: dict, evaluation: dict) -> FailureCategory:
        if evaluation.get("passed", True):
            raise ValueError("classify() should only be called for a failed evaluation")

        error = str(evaluation.get("error", "")).lower()

        if "timeouterror" in error:
            return FailureCategory.INFINITE_LOOP
        if "httpstatuserror" in error:
            return FailureCategory.TOOL_RESPONSE_ERROR
        if "runtimeerror" in error and "subprocessagent" in error:
            return FailureCategory.TOOL_CALL_ERROR
        if "validationerror" in error or "jsonschema" in error:
            return FailureCategory.PROMPT_DEFECT
        if "context" in error and "overflow" in error:
            return FailureCategory.CONTEXT_OVERFLOW

        tool_call_accuracy = evaluation.get("tool_call_accuracy")
        if tool_call_accuracy is not None and tool_call_accuracy < 1.0:
            return FailureCategory.TOOL_CALL_ERROR

        return FailureCategory.UNKNOWN
