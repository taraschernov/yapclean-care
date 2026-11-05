# YapClean Care: what we believed, where the error hid, what is true

**Date:** 2026-11-04. **Scope:** everything we know about Care mode accuracy and usefulness as of
today. Companion files: the claim-by-claim list in `STATUS.md` and the per-clip
data in `TORGO_CARE_MODE_BENCHMARK.md`.

## 1. The hypothesis

Written into the Care README and a technical dossier:

1. Ordinary speech recognition fails on dysarthric and stuttered speech for two reasons: voice
   activity detection cuts the user off during long pauses (0.8-2.5 s), and Whisper-style decoders
   fall into repetition loops on broken syllables.
2. A reconstruction layer (an LLM prompt plus guardrails, named "CADSR-LM") can turn the broken
   transcript back into the intended sentence.
3. Therefore word error rate (WER) on atypical speech collapses: the dossier stated
   **71.8% -> 0.0% on TORGO**.

Parts 1 and the loop half of the reasoning are plausible and partly confirmed. Part 3 is false, and
part 2 is not supported.

## 2. Where the error hid

The number never came from audio. Five things made it look real:

| Hiding place | What it looked like | What it was |
|---|---|---|
| Rule-based test helper, step "known dysarthric corrections" | A cleanup algorithm | A table mapping the test's own inputs to the reference sentences (`quivers are dripple` -> `quivers a trifle`). |
| Manifest field `baseline_asr_hypothesis` | Recognizer output on the TORGO clips | Three strings typed by hand. The three average 71.4% WER against their references (the dossier says 71.8%, which we could not reproduce exactly). |
| Sample ids `torgo_0005`, `torgo_0011`, `torgo_0053` | Real TORGO recordings | Labels on those hand-typed strings. |
| Assertion `wer == 0.0` in the tests | Proof of perfect reconstruction | A test that passed because the answers were inside the code under test. |
| README: "zero hardcoded phonetic replacements or synthetic fixtures" | A guarantee | Written next to the very table it denied. |

Three process failures let it travel into public documents:

- **Two benchmarks existed side by side.** The real-audio run (12 clips, published 2026-10-14)
  gave about 60% WER; the fixture gave 0%. The dossier used the fixture.
- **A weak baseline flattered the layer.** Uncalibrated Whisper Small scored 110.8% average WER
  (looping, foreign-script garbage). Almost anything beats that, so the improvement was credited
  to Care when it came from a bigger model and from filters.
- **The correction never left a local branch.** The independent re-run of 2026-10-29 sat unpushed,
  and the published text was not amended.

The harness was written in AI-agent sessions; the human review that should have caught a
"perfect" result on a hard problem did not happen. A result of 0.0% on dysarthric speech should
have been treated as a red flag, not a headline.

## 3. How we found it

1. **2026-10-14, first contradiction.** The real-audio run on 12 TORGO clips gave about 60% WER,
   not 0%. It was recorded but did not trigger a review of the dossier.
2. **2026-10-29, independent re-run.** Each of the 12 WAV files went through production
   `whisper-large-v3` (Groq), then the current Care cleanup (`care_mode=True`), and WER was computed
   with a separate, minimal Levenshtein implementation. Result: raw 61.0%, after Care 61.4%.
   The cleanup layer changes nothing. Deepgram nova-3 (63.5%) and Gemini audio (70.7%) were not better.
3. **2026-11-04, tracing the 71.8%.** Searching the repository showed the number only in documents.
   Running the benchmark helper on the manifest's "ASR hypotheses" gave 64.3%, 75.0%, 75.0% before
   and exactly 0.0% after; reading the helper revealed the table. New tests that demand "no word
   in the output that was not in the input" failed on the public Care repository too, with the
   reference sentences as output. We then checked the production Care prompt for leaked answers:
   none, so the real-audio measurements are not contaminated.

## 4. The real picture

Measured on 12 real TORGO recordings (one reading passage, speakers with cerebral palsy or ALS,
no speaker adaptation). Independent re-run, WER %:

| Clip | Raw whisper-large-v3 | After Care cleanup | Deepgram nova-3 | Gemini audio |
|---|---|---|---|---|
| 0005 | 92.9 | 85.7 | 64 | 86 |
| 0011 | 66.7 | 66.7 | 67 | 50 |
| 0012 | 87.5 | 87.5 | 88 | 88 |
| 0018 | 37.5 | 50.0 | 25 | 38 |
| 0019 | 33.3 | 33.3 | 33 | 89 |
| 0026 | 50.0 | 50.0 | 38 | 88 |
| 0044 | 70.0 | 70.0 | 90 | 50 |
| 0053 | 12.5 | 12.5 | 25 | 50 |
| 0056 | 91.7 | 91.7 | 100 | 92 |
| 0077 | 58.3 | 58.3 | 58 | 67 |
| 0084 | 76.9 | 76.9 | 92 | 62 |
| 0092 | 54.5 | 54.5 | 82 | 91 |
| **Average** | **61.0** | **61.4** | **63.5** | **70.7** |

Verdict on each part of the hypothesis:

| Hypothesis | Status | Evidence |
|---|---|---|
| Decoders loop on atypical speech | **Confirmed** | In the 2026-10-14 runs Whisper Small looped (130+ tokens on clip 0012) and produced Telugu/IPA/CJK garbage on clips 0012, 0026 and 0084 (which configuration produced which is inconsistent across the old reports). |
| A repetition penalty and filters stop it | **Confirmed, with a cost** | Loops and garbage no longer reach the document; the user gets an empty result and must repeat. |
| A bigger model helps | **Supported** | Small: about 65% (calibrated run of 2026-10-14) or about 78% (grid search); large-v3: 61%. The two local numbers were never reconciled and not re-run independently. |
| LLM reconstruction lowers WER | **Refuted** | 61.0% -> 61.4%. It cannot recover words the recogniser never heard. |
| Another engine is better | **Refuted on this set** | Deepgram 63.5%, Gemini 70.7%. Best of three per clip would reach about 52%. |
| Pause-tolerant recording matters | **Untested** | The app avoids silence cut-offs by using a hotkey toggle; nobody measured how often a cut-off hurts. |
| De-stuttering works | **Only on hand-written text** | No real stuttered audio has been measured. |
| Speaker adaptation would help | **Untested** | Not attempted. |

Limits of all of the above: twelve clips, one passage, read speech, mixed severity, no real users.

## 5. Practical value

What a person gets today, without exaggeration:

- **Mild and moderate speech** (clips like 0053, 0019, 0018): readable output, 12-38% WER. Typing
  hands-free into any Windows application is a real gain over no input at all.
- **Severe speech** (clips like 0005, 0012, 0056): 85-92% WER. Most words are still wrong; this is
  not a keyboard replacement.
- **Protection:** looping text, foreign-script garbage, refusal sentences from the language model
  and sentences invented after silence are filtered out, so the document is not polluted.
- **Cost model:** free with the user's own keys; 50% off managed cloud plans on request.
- **Not delivered:** any accuracy gain from the cleanup layer; screen-reader, switch or keyboard-only
  support; offline operation of the whole chain (only recognition runs offline).

Who should not rely on it yet: people with severe dysarthria who need dependable text, and anyone
who needs verified screen-reader compatibility.

## 6. What would change the picture

1. Speaker adaptation: vocabulary biasing and small-model fine-tuning on 15-30 minutes of one
   person's recordings, evaluated on held-out sentences against the 61% baseline.
2. Real recordings with consent, including stuttered speech and Bulgarian/Ukrainian, to replace
   hand-written test strings.
3. Reconciling the two local-model numbers and measuring latency and memory.
4. Testing with real users and NVDA/Narrator, then fixing what they report.

## 7. Controls added so it cannot repeat

- No published number without a raw results file made from real audio.
- Hand-written strings are labelled as such in code and ids; tests state they are not benchmarks.
- A test fails if the rule-based helper outputs a word that was not in its input or equals the
  reference sentence.
- README, site and technical documents are checked against code and measurements before it goes out.
- Corrections are pushed in the same change that finds them.
