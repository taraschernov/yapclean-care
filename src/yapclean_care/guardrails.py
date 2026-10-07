"""Quality guardrails for LLM formatting/translation outputs.

The token-fidelity checks compare the LLM candidate against the source text
with an *order-sensitive* word-level diff. Any added, missing, reordered, or
replaced word token is treated as hallucinated content: the candidate is
rejected and the original source text is returned as the baseline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GuardrailDecision:
    """Decision returned by quality guardrail checks."""

    accepted: bool
    output_text: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class TokenDiff:
    """One word-level deviation between the source and candidate tokens.

    ``kind`` is one of:
      - ``"added"``: the token exists in the candidate but not in the source,
      - ``"missing"``: the token exists in the source but not in the candidate,
      - ``"replaced"``: a source token was substituted by a different token at
        the same alignment position (an adjacent missing+added pair folded
        into one entry).
    A reordering surfaces as a ``"missing"`` token later balanced by an
    ``"added"`` token (the pair is kept separate when the tokens are equal).
    """

    kind: str
    source_index: int | None
    candidate_index: int | None
    source_token: str | None
    candidate_token: str | None


def apply_format_quality_guardrails(
    source_text: str,
    candidate_text: str,
    *,
    max_length_ratio: float = 2.5,
    min_source_length_for_ratio: int = 20,
    min_token_count_for_overlap: int = 6,
    min_token_overlap: float = 0.35,
    allow_token_rewrite: bool = False,
) -> GuardrailDecision:
    """Validate formatting output against hallucination/over-rewrite patterns.

    When ``allow_token_rewrite`` is False (default):
    The candidate must preserve the source's words and their order exactly.
    Capitalization and repeated horizontal whitespace may change freely.
    Punctuation, line breaks, and every word-level deviation (added, missing,
    reordered, or replaced) fall back to the source text.

    When ``allow_token_rewrite`` is True (e.g. user specified custom instructions):
    Lexical changes and semantic paraphrasing are permitted, while still
    strictly preventing dangerous shell/command injections, excessive runaway
    expansion, and empty payloads.

    ``min_token_count_for_overlap`` and ``min_token_overlap`` are retained for
    backward compatibility and are no longer used.
    """
    source = source_text.strip()
    candidate = candidate_text.strip()

    if not candidate:
        return GuardrailDecision(
            accepted=False,
            output_text=source,
            reason="empty_output",
        )

    if _is_excessive_expansion(
        source=source,
        candidate=candidate,
        max_length_ratio=max_length_ratio,
        min_source_length=min_source_length_for_ratio,
    ):
        return GuardrailDecision(
            accepted=False,
            output_text=source,
            reason="excessive_expansion",
        )

    if not allow_token_rewrite and _has_token_diff_mismatch(source, candidate):
        return GuardrailDecision(
            accepted=False,
            output_text=source,
            reason="token_diff_mismatch",
        )

    if _has_unsafe_punctuation_change(source, candidate, allow_token_rewrite=allow_token_rewrite):
        return GuardrailDecision(
            accepted=False,
            output_text=source,
            reason="unsafe_punctuation_change",
        )

    if allow_token_rewrite:
        if _has_conversational_preamble(candidate, source):
            return GuardrailDecision(
                accepted=False,
                output_text=source,
                reason="conversational_preamble",
            )
        source_tokens = _tokenize(source)
        candidate_tokens = _tokenize(candidate)
        if len(source_tokens) >= 4:
            overlap = _token_overlap_ratio(source_tokens, candidate_tokens)
            if overlap < 0.25:
                return GuardrailDecision(
                    accepted=False,
                    output_text=source,
                    reason="insufficient_token_overlap",
                )

    return GuardrailDecision(accepted=True, output_text=candidate)


def apply_translation_quality_guardrails(
    source_text: str,
    candidate_text: str,
    *,
    max_length_ratio: float = 3.0,
    min_source_length_for_ratio: int = 20,
) -> GuardrailDecision:
    """Validate translation output against runaway expansion/empty payloads.

    Translation legitimately rewrites every word, so no token-fidelity check is
    applied here; only empty payloads and runaway expansion are rejected.
    """
    source = source_text.strip()
    candidate = candidate_text.strip()

    if not candidate:
        return GuardrailDecision(
            accepted=False,
            output_text=source,
            reason="empty_output",
        )

    if _is_excessive_expansion(
        source=source,
        candidate=candidate,
        max_length_ratio=max_length_ratio,
        min_source_length=min_source_length_for_ratio,
    ):
        return GuardrailDecision(
            accepted=False,
            output_text=source,
            reason="excessive_expansion",
        )

    return GuardrailDecision(accepted=True, output_text=candidate)


def apply_strict_token_guardrails(
    source_text: str,
    candidate_text: str,
    *,
    max_length_ratio: float = 2.5,
    min_source_length_for_ratio: int = 20,
) -> GuardrailDecision:
    """Strict word-for-word fidelity check between source and candidate.

    The candidate is accepted only when its ``\\w+`` tokens match the source
    tokens exactly, in the same order. Any added, missing, reordered, or
    replaced word rejects the candidate with reason ``token_diff_mismatch``
    and falls back to the source text.
    """
    source = source_text.strip()
    candidate = candidate_text.strip()

    if not candidate:
        return GuardrailDecision(
            accepted=False,
            output_text=source,
            reason="empty_output",
        )

    if _is_excessive_expansion(
        source=source,
        candidate=candidate,
        max_length_ratio=max_length_ratio,
        min_source_length=min_source_length_for_ratio,
    ):
        return GuardrailDecision(
            accepted=False,
            output_text=source,
            reason="excessive_expansion",
        )

    if _has_token_diff_mismatch(source, candidate):
        return GuardrailDecision(
            accepted=False,
            output_text=source,
            reason="token_diff_mismatch",
        )

    return GuardrailDecision(accepted=True, output_text=candidate)


def _is_excessive_expansion(
    source: str,
    candidate: str,
    *,
    max_length_ratio: float,
    min_source_length: int,
) -> bool:
    if len(source) < min_source_length:
        return False
    if len(source) == 0:
        return False

    return len(candidate) > len(source) * max_length_ratio


def _tokenize_list_aware(text: str) -> list[str]:
    # Strip leading list item numerals so e.g. "1. First ...\n2. Second ..." does not treat '1', '2' as content tokens
    clean = re.sub(r"(?m)^\s*\d+[\.)]\s*", "", text)
    return _tokenize(clean)


def _has_token_diff_mismatch(source: str, candidate: str) -> bool:
    return _tokenize_list_aware(source) != _tokenize_list_aware(candidate)


_CONVERSATIONAL_PREAMBLE_RE = re.compile(
    r"^(?:here is|here's|sure,|certainly,|i have cleaned|cleaned (?:version|transcript):|вот (?:ваш|исправленный|текст)|конечно,|перевод:|результат:)\b",
    re.IGNORECASE,
)


def _has_conversational_preamble(candidate: str, source: str) -> bool:
    cand_match = _CONVERSATIONAL_PREAMBLE_RE.search(candidate.strip())
    if not cand_match:
        return False
    src_match = _CONVERSATIONAL_PREAMBLE_RE.search(source.strip())
    return src_match is None


def _token_overlap_ratio(source_tokens: list[str], candidate_tokens: list[str]) -> float:
    if not source_tokens:
        return 1.0
    source_set = set(source_tokens)
    candidate_set = set(candidate_tokens)
    shared = source_set.intersection(candidate_set)
    return len(shared) / float(len(source_set))


_CLI_COMMAND_PREFIXES = (
    "git ", "rm ", "rmdir ", "del ", "format ", "remove-item",
    "curl ", "npm ", "cargo ", "powershell", "cmd ", "bash ", "sh ",
    "docker ", "kubectl ", "pip ", "python ", "invoke-expression", "iex ",
    "clear-recyclebin", "drop table", "drop database", "echo ",
    "dir ", "terraform ", "wsl ", "sudo ", "clean "
)
_DESTRUCTIVE_COMMAND_INJECTION_RE = re.compile(
    r"(?:[\r\n;]|^)\s*(?:rm\s+-[a-z]*r[a-z]*|rmdir|del\s+|format\s+[a-z]:|remove-item|drop\s+table|drop\s+database|shutdown|reboot)\b",
    re.IGNORECASE,
)
_DANGEROUS_SHELL_OPERATORS_RE = re.compile(r"&&|\|\||`|\$\(|\||>|<")
_BASE_SAFE_PUNCTUATION_RE = re.compile(r'[\s.,!?:;—–\-"\'«»()\[\]…•]+')


def _is_cli_command(text: str) -> bool:
    normalized = text.strip().casefold()
    return any(normalized.startswith(prefix) for prefix in _CLI_COMMAND_PREFIXES)


def _introduces_command_injection(source: str, candidate: str) -> bool:
    source_lower = source.casefold()
    for line in candidate.splitlines():
        line_clean = line.strip().casefold()
        for prefix in _CLI_COMMAND_PREFIXES:
            if line_clean.startswith(prefix) and prefix not in source_lower:
                return True
    return False


def _strip_safe_formatting(text: str) -> str:
    # Strip markdown headers at start of line: e.g. "^#+ "
    text = re.sub(r"(?m)^\s*#+\s+", "", text)
    # Strip markdown paired bold/italic: e.g. "**bold**" or "*italic*"
    text = re.sub(r"\*\*([^\*\s][^\*]*?[^\*\s])\*\*", r"\1", text)
    text = re.sub(r"\*([^\*\s][^\*]*?[^\*\s])\*", r"\1", text)
    # Strip bullet points and list dashes at start of line
    text = re.sub(r"(?m)^\s*[•\-]\s+", "", text)
    # Strip list item numerals: "1. " or "1) " at start of line
    text = re.sub(r"(?m)^\s*\d+[\.)]\s*", "", text)
    return _BASE_SAFE_PUNCTUATION_RE.sub("", text).casefold()


def _has_unsafe_punctuation_change(
    source: str, candidate: str, allow_token_rewrite: bool = False
) -> bool:
    """Allow safe natural language punctuation while blocking dangerous command injection."""
    # If source is a CLI command, preserve strict exact punctuation:
    if _is_cli_command(source):
        normalized_source = re.sub(r"[ \t]+", " ", source).casefold()
        normalized_candidate = re.sub(r"[ \t]+", " ", candidate).casefold()
        return normalized_source != normalized_candidate

    # If candidate introduces dangerous command separators or shell operators not in source:
    if _DANGEROUS_SHELL_OPERATORS_RE.search(candidate) and not _DANGEROUS_SHELL_OPERATORS_RE.search(source):
        return True

    # If candidate introduces newline/delimiter before a destructive command:
    if _DESTRUCTIVE_COMMAND_INJECTION_RE.search(candidate) and not _DESTRUCTIVE_COMMAND_INJECTION_RE.search(source):
        return True

    # If candidate introduces a CLI command prefix not present in source:
    if _introduces_command_injection(source, candidate):
        return True

    if allow_token_rewrite:
        return False

    # Safe natural punctuation check: strip safe punctuation characters and check if underlying non-whitespace text matches
    stripped_source = _strip_safe_formatting(source)
    stripped_candidate = _strip_safe_formatting(candidate)
    return stripped_source != stripped_candidate


def _token_diff(source_tokens: list[str], candidate_tokens: list[str]) -> list[TokenDiff]:
    """Return the order-sensitive word diff between two token sequences.

    Implemented as a longest-common-subsequence (LCS) alignment:
      - a source token with no match in the candidate is ``"missing"``,
      - a candidate token with no match in the source is ``"added"``,
      - an adjacent missing+added pair with different tokens is folded into a
        single ``"replaced"`` entry (a word substitution at one position),
      - a reordering surfaces as a ``"missing"`` token later balanced by an
        ``"added"`` token (the pair is kept separate when the tokens match).
    """
    if source_tokens == candidate_tokens:
        return []

    table = _lcs_table(source_tokens, candidate_tokens)
    diffs: list[TokenDiff] = []
    source_index = 0
    candidate_index = 0

    while source_index < len(source_tokens) and candidate_index < len(candidate_tokens):
        if source_tokens[source_index] == candidate_tokens[candidate_index]:
            source_index += 1
            candidate_index += 1
        elif (
            table[source_index + 1][candidate_index]
            >= table[source_index][candidate_index + 1]
        ):
            diffs.append(
                TokenDiff(
                    kind="missing",
                    source_index=source_index,
                    candidate_index=None,
                    source_token=source_tokens[source_index],
                    candidate_token=None,
                )
            )
            source_index += 1
        else:
            diffs.append(
                TokenDiff(
                    kind="added",
                    source_index=None,
                    candidate_index=candidate_index,
                    source_token=None,
                    candidate_token=candidate_tokens[candidate_index],
                )
            )
            candidate_index += 1

    while source_index < len(source_tokens):
        diffs.append(
            TokenDiff(
                kind="missing",
                source_index=source_index,
                candidate_index=None,
                source_token=source_tokens[source_index],
                candidate_token=None,
            )
        )
        source_index += 1

    while candidate_index < len(candidate_tokens):
        diffs.append(
            TokenDiff(
                kind="added",
                source_index=None,
                candidate_index=candidate_index,
                source_token=None,
                candidate_token=candidate_tokens[candidate_index],
            )
        )
        candidate_index += 1

    return _fold_replacements(diffs)


def _fold_replacements(diffs: list[TokenDiff]) -> list[TokenDiff]:
    """Fold an adjacent missing+added pair into a single ``"replaced"`` entry.

    The fold is applied only when the two tokens differ; an adjacent pair of
    equal tokens indicates a reordering and is kept as missing+added.
    """
    folded: list[TokenDiff] = []
    index = 0
    while index < len(diffs):
        current = diffs[index]
        if (
            index + 1 < len(diffs)
            and current.kind == "missing"
            and diffs[index + 1].kind == "added"
            and current.source_token != diffs[index + 1].candidate_token
        ):
            folded.append(
                TokenDiff(
                    kind="replaced",
                    source_index=current.source_index,
                    candidate_index=diffs[index + 1].candidate_index,
                    source_token=current.source_token,
                    candidate_token=diffs[index + 1].candidate_token,
                )
            )
            index += 2
        else:
            folded.append(current)
            index += 1
    return folded


def _lcs_table(source_tokens: list[str], candidate_tokens: list[str]) -> list[list[int]]:
    """Build the LCS dynamic-programming table for two token sequences."""
    rows = len(source_tokens) + 1
    cols = len(candidate_tokens) + 1
    table = [[0] * cols for _ in range(rows)]
    for row in range(rows - 2, -1, -1):
        for col in range(cols - 2, -1, -1):
            if source_tokens[row] == candidate_tokens[col]:
                table[row][col] = table[row + 1][col + 1] + 1
            else:
                table[row][col] = max(table[row + 1][col], table[row][col + 1])
    return table


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)
