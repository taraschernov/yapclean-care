"""Multi-profile unit checks for the rule-based cleanup helper (hand-written strings).

These are not recognition benchmarks: the inputs are illustrations, not recognizer output.
Phoneme slips (profile A) are covered in test_dysarthria_benchmark.py, which asserts the rules
do NOT repair them. The assistive rules fix repeated syllables and pause fragments (B, C) and
over-correct fluent speech (D: 'so-so' -> 'so'), which is why Care Mode is an explicit toggle.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Ensure src is in sys.path when executed directly
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pytest

from yapclean_care.benchmark_profiles import (
    BENCHMARK_PROFILES,
    BenchmarkSample,
)
from yapclean_care.cadsr_adapter import (
    CADSRDysarthriaPromptAdapter,
    StandardPromptFilter,
)
from yapclean_care.wer_metrics import compute_wer


@pytest.fixture
def cadsr_adapter() -> CADSRDysarthriaPromptAdapter:
    return CADSRDysarthriaPromptAdapter()


@pytest.fixture
def standard_filter() -> StandardPromptFilter:
    return StandardPromptFilter()


def test_profile_b_stuttering_and_cluttering(
    cadsr_adapter: CADSRDysarthriaPromptAdapter,
    standard_filter: StandardPromptFilter,
) -> None:
    """Verify CADSR resolves sound repetitions and blocks where standard filter fails."""
    samples = [s for s in BENCHMARK_PROFILES if s.profile == "B"]
    assert len(samples) >= 3

    for sample in samples:
        base_res = compute_wer(sample.reference, sample.baseline_raw)
        std_res = compute_wer(sample.reference, standard_filter.normalize(sample.baseline_raw))
        assist_res = compute_wer(sample.reference, cadsr_adapter.normalize(sample.baseline_raw))

        # Standard filter leaves hyphenated sub-word fragments intact
        assert base_res.wer >= 0.40, f"Expected stuttering WER > 40% for {sample.id}"
        assert std_res.wer >= 0.40, f"Standard filter cannot de-stutter sub-word fragments for {sample.id}"
        # Assistive filter collapses all repetitions and blocks
        assert assist_res.wer == 0.0, f"Assistive filter must perfectly reconstruct {sample.id}"


def test_profile_c_breath_pauses_and_spasms(
    cadsr_adapter: CADSRDysarthriaPromptAdapter,
    standard_filter: StandardPromptFilter,
) -> None:
    """Verify CADSR fuses prolonged intra-sentence breath pauses and spasm gaps."""
    samples = [s for s in BENCHMARK_PROFILES if s.profile == "C"]
    assert len(samples) >= 3

    for sample in samples:
        base_res = compute_wer(sample.reference, sample.baseline_raw)
        std_res = compute_wer(sample.reference, standard_filter.normalize(sample.baseline_raw))
        assist_res = compute_wer(sample.reference, cadsr_adapter.normalize(sample.baseline_raw))

        # Baseline and Standard Prompt preserve pause ellipses and fragmented syllables
        assert base_res.wer >= 0.25, f"Expected pause fragmentation WER for {sample.id}"
        assert std_res.wer >= 0.25, f"Standard prompt must not guess intra-sentence ellipsis meaning for {sample.id}"
        # Assistive filter fuses pauses into smooth sentence
        assert assist_res.wer == 0.0, f"Assistive filter must reconstruct {sample.id}"


def test_profile_d_control_fluent_speech_degradation_check(
    cadsr_adapter: CADSRDysarthriaPromptAdapter,
    standard_filter: StandardPromptFilter,
) -> None:
    """CRITICAL CHECK: Does the Assistive Filter degrade normal fluent speech?

    Verifies that:
    1. Standard filter achieves 0.0% WER (preserves casual idioms, slang, reduplications).
    2. Assistive filter degrades fluent speech through over-correction ('so-so' -> 'so',
       'bye-bye' -> 'bye') and truncation ('no, no, no' -> 'no').
    This empirical regression proves why an explicit UI toggle (Care Mode) is mandatory.
    """
    samples = [s for s in BENCHMARK_PROFILES if s.profile == "D"]
    assert len(samples) >= 5

    total_std_wer = 0.0
    total_assist_wer = 0.0
    degraded_cases: list[str] = []

    for sample in samples:
        std_norm = standard_filter.normalize(sample.baseline_raw)
        std_res = compute_wer(sample.reference, std_norm)
        total_std_wer += std_res.wer

        # Standard filter must NEVER degrade fluent speech
        assert std_res.wer == 0.0, f"Standard filter degraded fluent case {sample.id}: {std_norm}"

        assist_norm = cadsr_adapter.normalize(sample.baseline_raw)
        assist_res = compute_wer(sample.reference, assist_norm)
        total_assist_wer += assist_res.wer

        if assist_res.wer > 0.0:
            degraded_cases.append(sample.id)

    # Standard filter maintains perfect 0.0% WER on fluent control
    avg_std = total_std_wer / len(samples)
    assert avg_std == 0.0, "Standard filter must have 0.0% WER on control group"

    # Assistive filter exhibits clear over-correction / truncation regression
    avg_assist = total_assist_wer / len(samples)
    assert avg_assist > 0.0, "Assistive filter must exhibit measurable degradation on fluent edge cases"
    assert len(degraded_cases) >= 3, f"Expected multiple over-correction regressions, got: {degraded_cases}"


def compute_benchmark_matrix() -> dict[str, dict[str, float]]:
    """Compute aggregate WER matrix across all 4 profiles and 3 processing pipelines."""
    adapter = CADSRDysarthriaPromptAdapter()
    std_filter = StandardPromptFilter()

    matrix: dict[str, dict[str, float]] = {
        "A": {"baseline": 0.0, "standard": 0.0, "assistive": 0.0, "count": 0},
        "B": {"baseline": 0.0, "standard": 0.0, "assistive": 0.0, "count": 0},
        "C": {"baseline": 0.0, "standard": 0.0, "assistive": 0.0, "count": 0},
        "D": {"baseline": 0.0, "standard": 0.0, "assistive": 0.0, "count": 0},
    }

    for s in BENCHMARK_PROFILES:
        base_wer = compute_wer(s.reference, s.baseline_raw).wer
        std_wer = compute_wer(s.reference, std_filter.normalize(s.baseline_raw)).wer
        assist_wer = compute_wer(s.reference, adapter.normalize(s.baseline_raw)).wer

        p = matrix[s.profile]
        p["baseline"] += base_wer
        p["standard"] += std_wer
        p["assistive"] += assist_wer
        p["count"] += 1

    summary: dict[str, dict[str, float]] = {}
    for prof, data in matrix.items():
        cnt = data["count"]
        summary[prof] = {
            "baseline": round((data["baseline"] / cnt) * 100.0, 1),
            "standard": round((data["standard"] / cnt) * 100.0, 1),
            "assistive": round((data["assistive"] / cnt) * 100.0, 1),
            "gain_vs_base": round(((data["baseline"] - data["assistive"]) / cnt) * 100.0, 1),
        }
    return summary


def run_multi_profile_benchmark_cli() -> int:
    """Print multi-profile benchmark matrix in a formatted table."""
    summary = compute_benchmark_matrix()
    names = {
        "A": "Profile A (Phoneme slips)",
        "B": "Profile B (Stuttering & Cluttering)",
        "C": "Profile C (Breath Pauses / Spasms)",
        "D": "Profile D (Control / Fluent Speech)",
    }

    print("\n" + "=" * 88)
    print("  RULE-BASED CLEANUP CHECK ON HAND-WRITTEN STRINGS (NOT A RECOGNITION BENCHMARK)")
    print("=" * 88)
    print(f"{'Profile Cohort':<38} | {'Base ASR':<10} | {'Std Prompt':<10} | {'Assistive':<10} | {'Delta':<10}")
    print("-" * 88)

    for p in ["A", "B", "C", "D"]:
        d = summary[p]
        delta_str = f"{d['gain_vs_base']:>+6.1f}%"
        print(
            f"{names[p]:<38} | {d['baseline']:>8.1f}% | {d['standard']:>8.1f}% | "
            f"{d['assistive']:>8.1f}% | {delta_str:>10}"
        )

    print("=" * 88)
    print("  The rules fix repeated syllables and pause fragments (profiles B/C) and leave phoneme")
    print("  slips (profile A) untouched. They over-correct fluent speech (profile D), so Care Mode")
    print("  stays an explicit opt-in toggle. Inputs are hand-written: nothing about real speech.\n")
    return 0


if __name__ == "__main__":
    sys.exit(run_multi_profile_benchmark_cli())
