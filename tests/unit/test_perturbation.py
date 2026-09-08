from runtrail.dataset import (
    InMemoryDataset,
    PerturbedDataset,
    add_distractor_text,
    add_typo_noise,
    shuffle_whitespace,
)


def test_perturbed_dataset_transforms_input_and_keeps_ground_truth():
    base = InMemoryDataset([{"input": "what is 2+2", "ground_truth": "4"}])
    dataset = PerturbedDataset(base, perturb=add_distractor_text)

    cases = list(dataset)

    assert len(dataset) == 1
    assert cases[0]["input"].endswith("what is 2+2")
    assert cases[0]["input"] != "what is 2+2"
    assert cases[0]["ground_truth"] == "4"


def test_add_distractor_text_prefixes_input():
    assert add_distractor_text("hello").endswith("hello")
    assert add_distractor_text("hello") != "hello"


def test_shuffle_whitespace_preserves_words():
    original = "the quick brown fox"
    result = shuffle_whitespace(original, seed=1)
    assert result.split() == original.split()


def test_add_typo_noise_is_deterministic_for_a_given_seed():
    text = "the quick brown fox jumps"
    assert add_typo_noise(text, seed=1) == add_typo_noise(text, seed=1)


def test_perturbed_dataset_applied_to_agent_harness_robustness_check():
    base = InMemoryDataset([{"input": "the answer is four", "ground_truth": "four"}])
    dataset = PerturbedDataset(base, perturb=lambda text: add_typo_noise(text, seed=2))

    perturbed_input = next(iter(dataset))["input"]

    assert isinstance(perturbed_input, str)
    assert len(perturbed_input) == len("the answer is four")
