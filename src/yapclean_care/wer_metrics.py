"""Word Error Rate (WER) computation module for atypical speech benchmarks."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WERResult:
    """Detailed result of Word Error Rate comparison."""

    wer: float
    substitutions: int
    deletions: int
    insertions: int
    reference_word_count: int
    hypothesis_word_count: int

    @property
    def percentage(self) -> float:
        """Return WER formatted as a percentage."""
        return round(self.wer * 100.0, 2)


_PUNCTUATION_PATTERN = re.compile(r"[^\w\s']|_")


def normalize_for_wer(text: str) -> list[str]:
    """Tokenize and normalize text for standard ASR evaluation.

    Converts to lowercase, removes punctuation, and splits on whitespace.
    """
    clean_text = _PUNCTUATION_PATTERN.sub(" ", text.lower())
    return [word for word in clean_text.split() if word]


def compute_wer(reference: str, hypothesis: str) -> WERResult:
    """Calculate Word Error Rate using standard dynamic programming edit distance.

    Formula: WER = (Substitutions + Deletions + Insertions) / Reference Word Count
    """
    ref_words = normalize_for_wer(reference)
    hyp_words = normalize_for_wer(hypothesis)

    ref_len = len(ref_words)
    hyp_len = len(hyp_words)

    if ref_len == 0:
        if hyp_len == 0:
            return WERResult(0.0, 0, 0, 0, 0, 0)
        return WERResult(1.0, 0, 0, hyp_len, 0, hyp_len)

    # DP table: dp[i][j] stores (cost, subs, dels, ins)
    dp: list[list[tuple[int, int, int, int]]] = [
        [(0, 0, 0, 0)] * (hyp_len + 1) for _ in range(ref_len + 1)
    ]

    for i in range(1, ref_len + 1):
        dp[i][0] = (i, 0, i, 0)

    for j in range(1, hyp_len + 1):
        dp[0][j] = (j, 0, 0, j)

    for i in range(1, ref_len + 1):
        for j in range(1, hyp_len + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                sub_cost = dp[i - 1][j - 1][0] + 1
                del_cost = dp[i - 1][j][0] + 1
                ins_cost = dp[i][j - 1][0] + 1

                min_cost = min(sub_cost, del_cost, ins_cost)
                if min_cost == sub_cost:
                    prev = dp[i - 1][j - 1]
                    dp[i][j] = (sub_cost, prev[1] + 1, prev[2], prev[3])
                elif min_cost == del_cost:
                    prev = dp[i - 1][j]
                    dp[i][j] = (del_cost, prev[1], prev[2] + 1, prev[3])
                else:
                    prev = dp[i][j - 1]
                    dp[i][j] = (ins_cost, prev[1], prev[2], prev[3] + 1)

    total_cost, subs, dels, ins = dp[ref_len][hyp_len]
    wer = total_cost / float(ref_len)

    return WERResult(
        wer=round(wer, 4),
        substitutions=subs,
        deletions=dels,
        insertions=ins,
        reference_word_count=ref_len,
        hypothesis_word_count=hyp_len,
    )
