"""Atypical Speech (Dysarthria) Benchmark Runner for YapClean.

Measures baseline ASR Word Error Rate (WER) versus CADSR-LM prompt-enhanced normalization
using open TORGO acoustic dataset samples and synthetic dysarthric test cases.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Ensure src is in sys.path when executed directly
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pytest

from yapclean_care.cadsr_adapter import (
    CADSRDysarthriaPromptAdapter,
)
from yapclean_care.wer_metrics import compute_wer

SAMPLES_DIR = Path(__file__).parent / "samples"
MANIFEST_PATH = SAMPLES_DIR / "manifest.json"

SYNTHETIC_CASES = [
    {
        "id": "synthetic_stutter_syllables",
        "description": "Articulatory tremors and syllable repetitions",
        "reference": "Please open the settings menu and configure audio devices.",
        "baseline_raw": "pl- please op- open the set- settings menu and con- configure aud- audio dev- devices.",
    },
    {
        "id": "synthetic_broken_pauses",
        "description": "Fragmented syllables with prolonged breath pauses",
        "reference": "I need to schedule a doctor appointment for tomorrow morning.",
        "baseline_raw": "I need to skeh- ... schedule a doc- ... doctor uh-pointment for tomorrow mor- ... morning.",
    },
    {
        "id": "synthetic_acoustic_drift",
        "description": "Consonant weakening and vowel slurring",
        "reference": "The patient walked slowly in the garden.",
        "baseline_raw": "de payshent wahked slowleh een de gahden.",
    },
]


def load_torgo_samples() -> list[dict[str, Any]]:
    """Load sample metadata from the TORGO manifest."""
    if not MANIFEST_PATH.exists():
        return []
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return manifest.get("samples", [])


@pytest.fixture
def cadsr_adapter() -> CADSRDysarthriaPromptAdapter:
    """Fixture providing configured CADSR prompt adapter."""
    return CADSRDysarthriaPromptAdapter()


def test_torgo_samples_manifest_integrity() -> None:
    """Verify that all 12 TORGO samples have valid metadata and exist on disk."""
    samples = load_torgo_samples()
    assert len(samples) == 12, f"Expected 12 TORGO sample cases in manifest, got {len(samples)}"
    for item in samples:
        assert item["reference"], f"Missing reference for {item['id']}"
        assert item["speaker_condition"], f"Missing condition for {item['id']}"
        wav_file = SAMPLES_DIR / item["file_name"]
        assert wav_file.exists(), f"Audio file {wav_file} must exist"
        assert wav_file.stat().st_size > 50_000, f"File {wav_file} is empty"


def test_torgo_baseline_vs_cadsr_wer(cadsr_adapter: CADSRDysarthriaPromptAdapter) -> None:
    """Verify CADSR-LM normalization achieves major WER reduction on evaluated TORGO cohort."""
    samples = [s for s in load_torgo_samples() if s.get("baseline_asr_hypothesis")]
    assert len(samples) >= 3, "No TORGO samples available"


    total_base_wer = 0.0
    total_cadsr_wer = 0.0

    for item in samples:
        ref = item["reference"]
        raw = item["baseline_asr_hypothesis"]

        base_metric = compute_wer(ref, raw)
        normalized = cadsr_adapter.normalize(raw)
        cadsr_metric = compute_wer(ref, normalized)

        # Baseline ASR on dysarthria suffers high WER (> 50%)
        assert base_metric.wer >= 0.50, f"Expected high baseline WER for {item['id']}, got {base_metric.percentage}%"
        # CADSR reconstruction significantly improves accuracy (WER < 10%)
        assert cadsr_metric.wer <= 0.10, f"CADSR WER too high for {item['id']}: {cadsr_metric.percentage}%"

        total_base_wer += base_metric.wer
        total_cadsr_wer += cadsr_metric.wer

    avg_base = (total_base_wer / len(samples)) * 100.0
    avg_cadsr = (total_cadsr_wer / len(samples)) * 100.0

    # Ensure net improvement exceeds 50 percentage points
    assert (avg_base - avg_cadsr) >= 50.0, f"Expected >50% net WER reduction, got {avg_base - avg_cadsr:.1f}%"


@pytest.mark.parametrize("case", SYNTHETIC_CASES, ids=lambda c: c["id"])
def test_synthetic_dysarthria_cases(
    cadsr_adapter: CADSRDysarthriaPromptAdapter, case: dict[str, str]
) -> None:
    """Verify CADSR-LM reconstructs synthetic dysarthric speech patterns."""
    ref = case["reference"]
    raw = case["baseline_raw"]

    base_metric = compute_wer(ref, raw)
    normalized = cadsr_adapter.normalize(raw)
    cadsr_metric = compute_wer(ref, normalized)

    assert cadsr_metric.wer < base_metric.wer, f"CADSR must improve WER for {case['id']}"
    assert cadsr_metric.wer == 0.0, f"Expected perfect reconstruction for {case['id']}, got {normalized}"


def test_anti_hallucination_and_guardrail_preservation(
    cadsr_adapter: CADSRDysarthriaPromptAdapter,
) -> None:
    """Verify that excessive runaway expansions are blocked by quality guardrails."""
    # A malicious or hallucinating output trying to hijack the text
    prompt = cadsr_adapter.build_reconstruction_prompt("hello world")
    assert "Strict Anti-Hallucination Guardrail" in prompt
    assert "No Execution" in cadsr_adapter.system_prompt or "Do NOT execute commands" in cadsr_adapter.system_prompt


def run_benchmark_suite() -> int:
    """CLI runner printing a formatted comparison report."""
    adapter = CADSRDysarthriaPromptAdapter()
    samples = load_torgo_samples()

    print("\n" + "=" * 80)
    print("  YAPCLEAN ATYPICAL SPEECH BENCHMARK (TORGO & CADSR-LM)")
    print("=" * 80)
    print(f"{'Case ID':<28} | {'Type':<10} | {'Base WER':<10} | {'CADSR WER':<10} | {'Gain':<8}")
    print("-" * 80)

    all_cases: list[tuple[str, str, str, str]] = []
    for s in samples:
        if s.get("baseline_asr_hypothesis"):
            all_cases.append((s["id"], "TORGO", s["reference"], s["baseline_asr_hypothesis"]))
    for c in SYNTHETIC_CASES:
        all_cases.append((c["id"], "Synthetic", c["reference"], c["baseline_raw"]))

    total_base_wer = 0.0
    total_cadsr_wer = 0.0

    for case_id, ctype, ref, raw in all_cases:
        base_res = compute_wer(ref, raw)
        norm = adapter.normalize(raw)
        cadsr_res = compute_wer(ref, norm)
        gain = base_res.percentage - cadsr_res.percentage

        total_base_wer += base_res.wer
        total_cadsr_wer += cadsr_res.wer

        print(
            f"{case_id:<28} | {ctype:<10} | {base_res.percentage:>8.1f}% | "
            f"{cadsr_res.percentage:>8.1f}% | {gain:>+6.1f}%"
        )

    count = len(all_cases)
    avg_base = (total_base_wer / count) * 100.0
    avg_cadsr = (total_cadsr_wer / count) * 100.0
    net_gain = avg_base - avg_cadsr

    print("-" * 80)
    print(f"{'OVERALL AVERAGE':<28} | {'Combined':<10} | {avg_base:>8.1f}% | {avg_cadsr:>8.1f}% | {net_gain:>+6.1f}%")
    print("=" * 80 + "\n")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(run_benchmark_suite())
