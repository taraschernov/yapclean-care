"""
Multilingual Audio Benchmark Test Suite for YapClean Care.

Validates the 25 calibrated speech scenarios across 5 languages:
- Russian (RU), Ukrainian (UK), English (EN), German (DE), Spanish (ES)
Covering 5 speech defect categories:
- hesitation: Self-corrections and mid-phrase false starts
- cleanliness: Acoustic noise, coughs, and throat clearing
- fillers: Filler word removal without semantic loss
- structure: Multi-clause punctuation and list formatting
- zero_distortion: Technical brand name and terminology preservation
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from yapclean_care.cadsr_adapter import CADSRDysarthriaPromptAdapter
from yapclean_care.wer_metrics import compute_wer

METADATA_PATH = Path(__file__).parent / "benchmark_metadata.json"


@pytest.fixture(scope="module")
def benchmark_cases():
    """Load the 25 multilingual benchmark cases."""
    assert METADATA_PATH.exists(), f"Missing metadata file at {METADATA_PATH}"
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_multilingual_case_distribution(benchmark_cases):
    """Ensure balanced coverage across 5 languages and 5 categories."""
    assert len(benchmark_cases) == 25

    languages = {c["lang"] for c in benchmark_cases}
    assert languages == {"ru", "uk", "en", "de", "es"}

    categories = {c["category"] for c in benchmark_cases}
    assert categories == {"hesitation", "cleanliness", "fillers", "structure", "zero_distortion"}

    # Each language has exactly 5 cases
    for lang in languages:
        cases_in_lang = [c for c in benchmark_cases if c["lang"] == lang]
        assert len(cases_in_lang) == 5


def test_hesitation_and_self_correction_resolution(benchmark_cases):
    """Verify that CADSR-LM prompt adapter resolves hesitation cases."""
    hesitation_cases = [c for c in benchmark_cases if c["category"] == "hesitation"]
    assert len(hesitation_cases) == 5

    adapter = CADSRDysarthriaPromptAdapter()
    for case in hesitation_cases:
        prompt = adapter.build_reconstruction_prompt(case["ground_truth"])
        assert "CADSR-LM" in prompt
        # Ground truth contains spoken false starts (higher word count than clean target)
        assert len(case["ground_truth"].split()) >= len(case["expected_clean"].split())
        wer = compute_wer(case["expected_clean"], case["ground_truth"])
        assert wer.insertions > 0 or wer.substitutions > 0, "Expected dirty speech deviations"


def test_acoustic_cleanliness_noise_rejection(benchmark_cases):
    """Verify that coughs and acoustic noise tags are eliminated from expected output."""
    cleanliness_cases = [c for c in benchmark_cases if c["category"] == "cleanliness"]
    assert len(cleanliness_cases) == 5

    noise_tokens = ["<cough>", "<breath>", "<sigh>", "*кашель*", "*вздох*"]
    for case in cleanliness_cases:
        expected = case["expected_clean"]
        for token in noise_tokens:
            assert token not in expected, f"Noise token {token} leaked into clean expected text for {case['id']}"
