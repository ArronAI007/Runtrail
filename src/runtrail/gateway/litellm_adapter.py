from typing import Any


class LiteLLMAdapter:
    """Routes model calls (LLMJudge, agent LLM calls) through LiteLLM / One-API.

    Requires the 'gateway' extra: pip install 'runtrail[gateway]'.
    """

    def __init__(self, model: str, **litellm_kwargs: Any):
        self.model = model
        self.litellm_kwargs = litellm_kwargs

    def complete(self, prompt: str, **kwargs: Any) -> str:
        return self.complete_with_usage(prompt, **kwargs)[0]

    def complete_with_usage(self, prompt: str, **kwargs: Any) -> tuple[str, dict]:
        """Like complete(), but also returns litellm's real token usage —
        {"prompt_tokens", "completion_tokens", "total_tokens"} — for feeding
        into a Trace step's 'tokens' field.
        """
        try:
            import litellm
        except ImportError as exc:
            raise ImportError(
                "LiteLLMAdapter requires the 'gateway' extra: pip install 'runtrail[gateway]'"
            ) from exc

        response = litellm.completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **{**self.litellm_kwargs, **kwargs},
        )
        usage = getattr(response, "usage", None)
        tokens = (
            {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }
            if usage is not None
            else {}
        )
        return response.choices[0].message.content, tokens
