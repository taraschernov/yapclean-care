"""Unit checks for the rule-based cleanup helper used by the atypical-speech tests.

IMPORTANT - what this file is NOT: it is not a recognition benchmark. The strings below are
hand-written illustrations, not output of any speech recognizer, so no WER here says anything
about how well Care understands dysarthric speech. Real measurements on TORGO audio are in
docs/TORGO_CARE_MODE_BENCHMARK.md (independent re-run: about 61% WER; the cleanup layer
does not lower it).

What is checked: the deterministic rules collapse syllable repetitions and pause fragments,
and they do NOT repair phoneme slips or add words that were not in the input.
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

from yapclean_care.benchmark_profiles import BENCHMARK_PROFILES
from yapclean_care.cadsr_adapter import (
    CADSRDysarthriaPromptAdapter,
)
from yapclean_care.wer_metrics import compute_wer, normalize_for_wer

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


def test_rules_collapse_syllable_repetitions(cadsr_adapter: CADSRDysarthriaPromptAdapter) -> None:
    """Stuttered syllable repetitions are a pattern the rules can resolve."""
    case = SYNTHETIC_CASES[0]
    normalized = cadsr_adapter.normalize(case["baseline_raw"])
    assert compute_wer(case["reference"], normalized).wer == 0.0, normalized


def test_rules_resolve_pause_fragments_but_not_phoneme_slips(
    cadsr_adapter: CADSRDysarthriaPromptAdapter,
) -> None:
    """'doc- ... doctor' is resolvable; the slip 'uh-pointment' is not, and must stay wrong."""
    case = SYNTHETIC_CASES[1]
    normalized = cadsr_adapter.normalize(case["baseline_raw"])
    before = compute_wer(case["reference"], case["baseline_raw"]).wer
    after = compute_wer(case["reference"], normalized).wer
    assert after < before, normalized
    assert after > 0.0, f"rules must not know the intended word 'appointment': {normalized}"


def _phoneme_slip_cases() -> list[tuple[str, str, str]]:
    cases = [(c["id"], c["reference"], c["baseline_raw"]) for c in SYNTHETIC_CASES[2:]]
    cases += [(s.id, s.reference, s.baseline_raw) for s in BENCHMARK_PROFILES if s.profile == "A"]
    return cases


@pytest.mark.parametrize("case_id, reference, raw", _phoneme_slip_cases())
def test_rules_do_not_repair_phoneme_slips_or_invent_words(
    cadsr_adapter: CADSRDysarthriaPromptAdapter, case_id: str, reference: str, raw: str
) -> None:
    """Rules cannot know what the speaker meant: no new words, no reference-matching output."""
    normalized = cadsr_adapter.normalize(raw)
    invented = set(normalize_for_wer(normalized)) - set(normalize_for_wer(raw))
    assert not invented, f"{case_id}: rules produced words that were not in the input: {sorted(invented)}"
    assert compute_wer(reference, normalized).wer > 0.0, f"{case_id}: output equals the reference"


def test_anti_hallucination_and_guardrail_preservation(
    cadsr_adapter: CADSRDysarthriaPromptAdapter,
) -> None:
    """Verify that excessive runaway expansions are blocked by quality guardrails."""
    # A malicious or hallucinating output trying to hijack the text
    prompt = cadsr_adapter.build_reconstruction_prompt("hello world")
    assert "Strict Anti-Hallucination Guardrail" in prompt
    assert "No Execution" in cadsr_adapter.system_prompt or "Do NOT execute commands" in cadsr_adapter.system_prompt


def test_care_mode_guardrails_relax_overlap_and_catch_refusal() -> None:
    """Verify care_mode=True skips token overlap but catches conversational refusal preambles."""
    from yapclean_care.guardrails import apply_format_quality_guardrails

    # Syllable fragmentation rewrite passes in care_mode
    res = apply_format_quality_guardrails(
        source_text="pl- please op- open the set- settings",
        candidate_text="Please open the settings.",
        allow_token_rewrite=True,
        care_mode=True,
    )
    assert res.accepted is True
    assert res.output_text == "Please open the settings."

    # LLM refusal explanation is rejected as conversational preamble
    refusal = apply_format_quality_guardrails(
        source_text="The speaker is speaking with heavy slurring and spastic pauses here.",
        candidate_text="The input text consists of phonetic noise and unintelligible vocalizations.",
        allow_token_rewrite=True,
        care_mode=True,
    )
    assert refusal.accepted is False
    assert refusal.reason == "conversational_preamble"


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
