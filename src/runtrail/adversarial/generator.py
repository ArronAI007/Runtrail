from typing import Any

from runtrail.dataset.base import BaseDataset
from runtrail.dataset.memory_dataset import InMemoryDataset
from runtrail.gateway.litellm_adapter import LiteLLMAdapter

DEFAULT_ADVERSARIAL_PROMPT = """Rewrite the following question to be deliberately confusing, \
ambiguous, or misleading for an AI agent to answer, while the correct answer stays the same. \
Use techniques like irrelevant context, double negatives, or red herrings. Respond with ONLY \
the rewritten question, no explanation, no quotes.

Original question: {question}"""


class LLMAdversarialGenerator:
    """Uses an LLM (via LiteLLMAdapter, or any gateway with a compatible
    `.complete(prompt) -> str`) to generate adversarial rephrasings of
    existing cases — semantic attacks a fixed template (AdversarialDataset)
    can't produce. Requires the 'gateway' extra: pip install 'runtrail[gateway]'.
    """

    def __init__(
        self,
        model: str,
        *,
        prompt_template: str = DEFAULT_ADVERSARIAL_PROMPT,
        gateway: Any = None,
        **gateway_kwargs: Any,
    ):
        self.prompt_template = prompt_template
        self.gateway = gateway or LiteLLMAdapter(model, **gateway_kwargs)

    def generate(self, case: dict) -> dict:
        prompt = self.prompt_template.format(question=case["input"])
        rewritten = self.gateway.complete(prompt)
        return {**case, "input": rewritten.strip(), "adversarial_type": "llm_rephrase"}

    def generate_dataset(self, base: BaseDataset) -> InMemoryDataset:
        return InMemoryDataset([self.generate(case) for case in base])
