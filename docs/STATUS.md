# YapClean Care: status, built vs claimed

> **Written 2026-11-04.** An audit of our own earlier documents against the code and the raw
> measurements found that some claims (in this project's README and technical dossier) are wrong
> or unproven. This page lists them and supersedes every earlier statement that disagrees with it.
> Most of the code and documents were written with AI coding assistants (Claude, Gemini) under the
> maintainer's direction. Care mode lives in the proprietary YapClean Windows app; the open part
> is a small Python library (pre-roll buffer, pause-tolerant VAD class, decoder settings,
> guardrails, WER code, layout detection), tests and measurements.

How the error happened and was found: [INVESTIGATION_2026-11-04.md](INVESTIGATION_2026-11-04.md).

## 1. Summary

An audit of our own earlier documents against the code and the raw measurements found that the
headline result was not a measurement and several architecture claims describe things that do
not exist. What is real: a working Windows
dictation app with a Care mode that stops a recogniser's garbage from reaching the user's
document, and a small, honest TORGO measurement showing that, on its own, cleanup does not
make dysarthric speech more accurate. The gap that money could close is speaker adaptation,
which has not been attempted.

## 2. Claim ledger

Verdicts: **FALSE** = contradicted by evidence, **NOT BUILT** = no code, **UNVERIFIED** = no
measurement exists, **PARTIAL** = exists in a narrower form.

| # | Claim made earlier (README, technical dossier) | What the evidence shows | Verdict |
|---|---|---|---|
| 1 | TORGO WER "71.8% -> 0.0%" | Not measured on audio. 71.8% is the average WER of three hand-typed "baseline" strings; 0.0% came from a regex table that rewrote those strings into the reference sentences. Real run on the 12 TORGO recordings: raw `whisper-large-v3` 61.0% WER, 61.4% after Care cleanup. | **FALSE** |
| 2 | "Zero hardcoded replacements or synthetic fixtures" (Care README) | The adapter contained the answer table (`quivers are dripple` -> `quivers a trifle`). Removed in the commit that introduced this document. | **FALSE** |
| 3 | "CADSR-LM... ICASSP method" | The name is ours. It is an LLM prompt plus generic regex rules, not a published or trained method. No citation exists. | **FALSE** |
| 4 | Rust engine, embedded quantized `whisper.cpp`, 100% offline, <500 MB RAM | App = Tauri shell + Python sidecar (`faster-whisper`). No `whisper.cpp` anywhere. Offline covers speech recognition only; LLM cleanup needs a cloud or the user's own Ollama/key. RAM never measured. | **FALSE / UNVERIFIED** |
| 5 | <30 ms capture latency, 0.3-0.5 s insertion, 35 ms clipboard restore | Never measured. Clipboard restore no longer exists (the app now types text and leaves the clipboard untouched). Cloud round-trips take seconds. | **UNVERIFIED / obsolete** |
| 6 | Adaptive VAD (800-2,500 ms) and 1.5 s pre-roll buffer | Exist only as small classes in the Care library, tested on synthetic arrays and not wired into the app. In the app, recording is toggled by hotkey (press to start, press to stop), so nobody is cut off; that is the real mechanism.  | **PARTIAL** |
| 7 | `WS_EX_NOACTIVATE`: "zero focus theft from NVDA/JAWS/Narrator" | The flag is used on some overlay windows. The recording pill is deliberately allowed to take focus on first press by design. No screen-reader test was ever run. | **UNVERIFIED** |
| 8 | Windows, Linux and macOS | Windows x64 only. | **FALSE** |
| 9 | HID support for switches, sip-and-puff, foot pedals; earcons | No code. | **NOT BUILT** |
| 10 | Tier 3 relay on a Cloudflare Worker, anonymous ed25519 token, `YC-CARE-` NGO vouchers, partner clinics | The managed proxy runs on our VPS (Groq, Deepgram, Gemini). A `YC-CARE-` key prefix exists (10,000 words/month, BYOK). No voucher distribution, no NGO or clinic partners, no startup credits secured for Care. | **NOT BUILT / PARTIAL** |
| 11 | "No audio sent to non-EU servers", "GDPR Art. 9 compliant" | Cloud and BYOK modes send audio to US providers. No legal assessment was done. | **FALSE / UNVERIFIED** |
| 12 | Gemini/Groq free-tier limits ("no card required") | Copied by an agent, not re-checked. Our own rule is that free keys are for testing only; free-tier terms may allow provider use of content. Verify before advising vulnerable users. | **UNVERIFIED** |
| 13 | 25-case multilingual benchmark (Groq 80%, 299 ms) | Real, but it measures text cleanup of fluent, TTS-generated speech. It says nothing about atypical speech. | **PARTIAL** |
| 14 | "100% of the core is MIT / open" | The Care repo is a ~1,500-line Python library. The working app that implements Care mode is the proprietary YapClean app. Licence text also differs: dual MIT/Apache-2.0, MIT (draft), Apache badge (README). | **PARTIAL** |
| 15 | Pilot with 20+ users, community calibration, WCAG 2.1 AAA | Planned only. No user with a speech disability has used or tested Care. WCAG was never audited. | **NOT BUILT** |

Also to check: the 12 TORGO WAV files are committed to this repository; whether TORGO's licence allows redistribution and commercial use has not been confirmed.

## 3. What Care does today

In the YapClean app (closed source), `care_mode` forces text cleanup even for very short
phrases, runs it at temperature 0 with a prompt that says "reconstruct, never invent", relaxes
the word-overlap guardrail for broken syllables (injection and runaway-expansion checks stay),
and drops garbage before it reaches the document: foreign-script and IPA output, refusal text
such as "the input consists of unintelligible noise", and sentences invented after trailing
silence. Local recognition uses a tuned repetition penalty so Whisper does not loop on
stutters. Recording is toggled by hotkey (press to start, press to stop), so nobody is cut off.
Text is typed into the active field of any Windows app. It is free with the user's own keys.
The guardrail code is published in `src/yapclean_care/guardrails.py`.

## 4. What it is good for, and where it is not

Measured on 12 real TORGO clips (one reading passage, no users), independent re-run on
2026-10-29, WER averaged: raw `whisper-large-v3` **61.0%**, after Care cleanup **61.4%**,
Deepgram nova-3 63.5%, Gemini audio 70.7%; best of three per clip about 52%. Local
Whisper Small with the tuned penalty is worse (about 78% in the grid search, not re-run
independently). Per clip, cloud recognition reached 12.5-37.5% on mild cases and 85-92% on
severe ones.

Honest reading:
- Useful today for **mild-to-moderate** atypical speech and for stuttering-like disfluency:
  hands-free typing in any Windows app, with the output protected from garbage. For severe
  dysarthria roughly half the words are still wrong; it is an assistive aid, not a
  replacement for a keyboard.
- The LLM cleanup does **not** lower WER on dysarthric speech. It cannot recover words the
  recogniser never heard. The gain over uncalibrated Whisper comes from the larger model and
  the guardrails.
- Twelve clips from one passage are too few for strong claims, and read speech is not
  conversation.

## 5. What is not solved

1. No method that actually improves accuracy for an individual speaker (see section 6).
2. No data from real users; no Bulgarian or Ukrainian atypical-speech data at all.
3. No screen-reader, switch or keyboard-only accessibility testing; no WCAG audit.
4. Latency and memory unmeasured; no Linux or macOS build.
5. No privacy or legal assessment for health-related audio sent to cloud providers; TORGO
   licence question open.
6. The open/proprietary boundary is undefined: what would be funded, and published, is not
   yet separated from the commercial app.

## 6. Open work

The one thing that can move WER is **speaker adaptation**: personal vocabulary biasing and
fine-tuning a small model on 15-30 minutes of one person's recordings, evaluated on held-out
sentences against the speaker-independent baseline (61% on the TORGO set). Planned order:

1. **Evidence base:** a reproducible harness that publishes raw results, latency and memory
   measurement, a privacy review of health-related audio, and the TORGO licence question.
2. **Consent-first recording tool** (local storage) and recruitment of volunteers; a first open
   evaluation set in Bulgarian, Ukrainian and English, only with explicit consent to share.
3. **Adaptation experiments** (vocabulary biasing, small-model fine-tuning); negative results are
   published too.
4. **Care module in the app**, tested by real users with NVDA/Narrator and switch access, then fixes.

Open decisions: how volunteers are compensated, which parts of Care live in the open repository
while the app stays proprietary, and one licence statement (Apache-2.0 OR MIT).
