import random
from collections.abc import Callable, Iterator
from typing import Any

from runtrail.dataset.base import BaseDataset


class PerturbedDataset(BaseDataset):
    """Wraps a BaseDataset and applies a perturbation function to each case's
    input, for testing Agent robustness against task variants — distinct from
    ToolMock, which perturbs tool *responses* rather than the task itself.

    Built-in perturbations here are deterministic, structural transforms
    (whitespace/typo noise, distractor text); semantic paraphrasing needs an
    LLM call, which callers can plug in as their own `perturb` function once
    LiteLLMAdapter/LLMJudge covers their model of choice.
    """

    def __init__(self, base: BaseDataset, perturb: Callable[[Any], Any]):
        self.base = base
        self.perturb = perturb

    def __iter__(self) -> Iterator[dict]:
        for case in self.base:
            yield {**case, "input": self.perturb(case["input"])}

    def __len__(self) -> int:
        return len(self.base)


def add_distractor_text(text: str, *, distractor: str = "(ignore this: irrelevant aside) ") -> str:
    return f"{distractor}{text}"


def shuffle_whitespace(text: str, *, seed: int = 0) -> str:
    rng = random.Random(seed)
    words = text.split(" ")
    return (" " * rng.randint(1, 3)).join(words) if len(words) > 1 else text


def add_typo_noise(text: str, *, seed: int = 0, swap_probability: float = 0.1) -> str:
    rng = random.Random(seed)
    chars = list(text)
    for i in range(len(chars) - 1):
        if chars[i].isalpha() and chars[i + 1].isalpha() and rng.random() < swap_probability:
            chars[i], chars[i + 1] = chars[i + 1], chars[i]
    return "".join(chars)
