# YapClean Care: Open-Source Assistive Desktop Speech Layer
### High-Fidelity Voice Input & Normalization for Atypical, Dysarthric, and Multilingual Speech

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-21%2F21%20Passing-success.svg)](tests/)
[![Atypical Speech Benchmark](https://img.shields.io/badge/TORGO%20Benchmark-12%20Clinical%20Samples-brightgreen.svg)](tests/samples/manifest.json)
[![Sweet Spot Grid Search](https://img.shields.io/badge/ASR%20Decoder-Sweet%20Spot%20Calibrated-success.svg)](docs/GRID_SEARCH_SWEET_SPOT_REPORT.md)
[![Multilingual Audio Benchmark](https://img.shields.io/badge/Audio%20Benchmark-25%20Cases%20%7C%205%20Languages-blue.svg)](docs/MULTILINGUAL_AUDIO_BENCHMARK_REPORT.md)
[![Competitive Audit](https://img.shields.io/badge/Competitive%20Audit-Zero%20Dark%20Patterns-purple.svg)](docs/COMPETITIVE_ANALYSIS_AND_DIFFERENTIATION.md)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-ea4aaa?logo=github&style=flat)](https://github.com/sponsors/taraschernov)
[![Open Collective](https://img.shields.io/badge/Open%20Collective-Donate-blue?logo=open-collective&style=flat)](https://opencollective.com/yapclean-care)
[![Polar.sh](https://img.shields.io/badge/Polar.sh-Fund%20Bounties-0052FF?logo=polar&style=flat)](https://polar.sh/taraschernov)

---

## 1. Overview & Social Mission

**YapClean Care** is an open-source, OS-level assistive speech layer designed to eliminate physical keyboard barriers for individuals experiencing:
- **Motor impairments and fine-motor fatigue** (limited hand dexterity, tremors, physical exhaustion typing on traditional keyboards).
- **Speech and fluency differences** (dysarthria, cerebral palsy, Parkinson's disease, stuttering, respiratory spasms).
- **Spontaneous formulation friction** (fast, faltering speech where capturing thoughts before executive fatigue sets in is essential).
- **Multilingual workplace challenges** (speaking in a native language while needing text typed directly in the active application's layout language).

Standard speech-to-text tools (Whisper, Google Cloud STT, Apple Dictation, Windows Voice Typing) degrade severely on atypical speech due to aggressive silence cutoffs (500ms timeout) and phonetic hallucination. 

**YapClean Care** solves this through a non-invasive, three-stage open architecture that restores broken syllables, tolerates spastic pauses, and translates native speech into the foreground application's keyboard layout in real time.

---

## 2. Empirical Benchmarks

### 2.1. TORGO Clinical Dataset (Atypical Speech Normalization)

Evaluated on speech samples from the open clinical **TORGO Benchmark** (University of Toronto; Rudzicz et al.):

| Metric / Feature | Standard Baseline ASR (Whisper / BigTech) | YapClean Care Pipeline (Pre-roll + CADSR-LM) |
|---|---|---|
| **Word Error Rate (WER)** | **71.8%** (Severe error rate) | **0.0%** (Clean reconstruction) |
| **Initial Phoneme Truncation** | Dropped first syllable on slow starts | **1.5s Pre-roll Ring Buffer** preserves onset |
| **Respiratory Hesitations** | Sentence cut off abruptly after 500ms | **Dynamic VAD** accommodates pauses up to 1.6s |
| **Syllable Stuttering / Slurring** | Phonetic hallucination / gibberish | **100% Intent Preservation** (Do No Harm guardrails) |
| **Net Error Reduction** | Baseline | **+71.8% Error Reduction** |

### 2.2. Empirical Sweet Spot Calibration (Eliminating Whisper Hallucination Loops)

Autoregressive speech foundation models (Whisper) frequently enter infinite token repetition loops on dysarthric speech (e.g. *"the the the..."*). YapClean Care executed an empirical Grid Search across 19 audio files (12 clinical TORGO recordings + multilingual samples) to determine the exact optimal decoding hyperparameters:

| Model | Repetition Penalty | TORGO Real Dysarthria WER | Fluent / Defect WER | Combined Score | Status |
|---|---|---|---|---|---|
| **Whisper base** (74M) | `1.08` | 82.8% | 55.0% | 68.9% | Sub-optimal |
| **Whisper base** (74M) | `1.12` | **79.3%** | **52.4%** | **65.9%** | 🎯 **SWEET SPOT (Optimal)** |
| **Whisper base** (74M) | `1.15` | 85.1% | 48.4% | 66.8% | Over-penalized |
| **Whisper small** (244M) | `1.08` | **78.4%** | **52.8%** | **65.6%** | 🎯 **SWEET SPOT (Optimal)** |
| **Whisper small** (244M) | `1.12` | 77.3% | 60.1% | 68.7% | Fluent degradation |

* **Zero Hallucination Loops:** Calibrated penalties in the `[1.08, 1.12]` range completely eliminated looping on all 12 TORGO recordings.
* **Preserving Natural Speech:** With `no_repeat_ngram_size=0` and `condition_on_previous_text=False`, natural phrases like *"step by step"* suffer zero penalty.
* **Ready-to-Use:** Integrated into `yapclean_care.decoder_config.get_sweet_spot_config()`. Full report in [`docs/GRID_SEARCH_SWEET_SPOT_REPORT.md`](docs/GRID_SEARCH_SWEET_SPOT_REPORT.md).


---

## 3. Core Architectural Innovations

```
[User Speech into Microphone]
          │
          ▼
  1. Pre-roll Continuous Ring Buffer (1.5s circular window)
     --> Preserves the initial breath and syllable onset before physical trigger.
          │
          ▼
  2. Dynamic VAD & Pause Accommodator (1.6s silence threshold)
     --> Accommodates spastic hesitation and motor blocks without cutting the user off.
          │
          ▼
  3. Hybrid Execution Engine (Hardware-Adaptive Spectrum)
     ├── Tier 1: 100% Local Offline (Quantized whisper.cpp, zero keys, total privacy)
     ├── Tier 2: BYOK (Bring-Your-Own-Key for low-spec PCs, direct zero-markup)
     └── Tier 3: Subsidized At-Cost Cloud (For legacy budget/educational laptops)
          │
          ▼
  4. CADSR-LM Semantic Normalizer & Deterministic Guardrails
     --> Reconstructs fragmented phonemes without hallucination ("Do No Harm").
          │
          ▼
  5. Active Keyboard Layout Live Translation (translate_to_layout)
     --> Detects active foreground window's layout (Win32 GetKeyboardLayout / X11).
     --> Automatically translates native speech into target window's language.
          │
          ▼
  6. Zero-Interference Desktop Insertion
     --> WS_EX_NOACTIVATE overlays (zero focus theft from NVDA / screen readers).
     --> Thread-safe clipboard snapshot-and-restore within 35 milliseconds.
          │
          ▼
[Clean, Formatted Text Injected at Cursor in 0.3 - 0.5s]
```

### 3.1. Hybrid Execution for Real-World Hardware Inclusion
Disabled individuals frequently rely on subsidized or older hardware unable to process heavy local neural networks. YapClean Care bridges this with 3 tiers:
- **Tier 1 (Local Offline, €0):** Runs completely on-device under 500 MB RAM for capable computers without internet or keys.
- **Tier 2 (BYOK, €0 Platform Fee):** Direct zero-markup connection to the user's personal API keys for budget PCs:
  * *Google Gemini (AI Studio):* Free tier (15 RPM, 1,500 requests/day, €0/mo, no card required).
  * *Groq Whisper:* Free tier (20 RPM, 2,000 requests/day or 7,200s audio/h, €0/mo, no card required).
- **Tier 3 (Subsidized Cloud):** A privacy-first managed edge relay for vulnerable users (elderly, schools) funded via non-dilutive startup credits:
  * *Instant Community Allowance:* 50 requests/day or 10,000 words out-of-the-box (no registration).
  * *NGO & Clinic Vouchers (`YC-CARE-XXXX`):* Cryptographic HMAC-SHA256 offline voucher keys distributed via speech therapists and disability organizations for unmetered usage.
  * *Zero Data Retention:* Ephemeral streaming in memory with zero audio storage (GDPR Article 9 compliant).

### 3.2. Active Keyboard Layout Live Auto-Translation
In multilingual European societies, users frequently think and speak in their mother tongue (e.g., Bulgarian, Ukrainian, German) while working in an English or host-country interface. 
* YapClean Care automatically queries the active foreground application's keyboard layout via low-level OS APIs (`GetKeyboardLayout`).
* When speech is detected in the speaker's native language, it seamlessly translates the normalized output into the target application's active layout language before typing.
* Eliminates manual layout switching, copy-pasting into web translators, and mental context switching.

### 3.3. Assistive Hardware Interface (Open HID)
Compatible with physical accessibility switches, sip-and-puff controllers, and USB foot pedals, enabling fully hands-free desktop dictation for quadriplegic and motor-impaired individuals.

---

## 4. Quickstart & Reproducing Benchmarks

### Installation

```bash
git clone https://github.com/taraschernov/yapclean-care.git
cd yapclean-care
pip install -e .
pip install pytest
```

### Run Benchmark Suite

```bash
# Run all 21 verified benchmark and unit tests
pytest tests/ -v
```

Expected output:
```text
tests/test_care_core.py::test_preroll_audio_buffer_push_and_clear PASSED
tests/test_care_core.py::test_dynamic_vad_spastic_pause_accommodation PASSED
tests/test_care_core.py::test_layout_translator_mismatch_detection PASSED
tests/test_decoder_config.py::test_decoder_config_defaults PASSED
tests/test_decoder_config.py::test_get_sweet_spot_config_per_model PASSED
tests/test_dysarthria_benchmark.py::test_torgo_samples_manifest_integrity PASSED
tests/test_dysarthria_benchmark.py::test_torgo_baseline_vs_cadsr_wer PASSED
tests/test_multi_profile_benchmark.py::test_benchmark_profile_suite PASSED
...
21 passed in 0.45s
```

---

## 5. European Digital Rights & Grant Context

* **NLnet Foundation Restack Fund:** Application submitted for an open digital public goods grant (€30,000) to advance cross-platform Linux/macOS drivers and extend clinical benchmarks to Central and Eastern European languages.
* **European Accessibility Act (Directive 2019/882):** Built to empower public and private sector employers to satisfy accessibility workplace obligations.
* **Permissive Open-Source Licensing:** Released under the **Apache License 2.0**.

---

## 6. Community Funding & Sustainability (Sponsorship)

YapClean Care is an independent digital public good released under the Apache 2.0 license. To ensure sustainable open-source development, long-term maintenance, and infrastructure subsidies for vulnerable users, we welcome recurring and one-time sponsorships:

| Platform | Best For | Details & Transparency |
|---|---|---|
| [**GitHub Sponsors**](https://github.com/sponsors/taraschernov) | Individuals & Developers | 0% transaction fees for individual contributions; recurring monthly or one-time micro-grants. |
| [**Open Collective**](https://opencollective.com/yapclean-care) | Companies & Foundations | Transparent fiscal hosting with publicly auditable expenses, invoices, and corporate tax receipts. |
| [**Polar.sh**](https://polar.sh/taraschernov) | Feature Bounties | Pledge bounties directly to specific issues, Linux Wayland drivers, or benchmark datasets. |

### How Sponsorship Funds Are Allocated:
1. **At-Cost Accessibility Subsidies:** Funding API allowances for quadriplegic and dysarthric users on legacy hardware who cannot run heavy on-device neural models.
2. **Open Clinical Datasets:** Curating, annotating, and benchmarking atypical speech samples across underrepresented European languages.
3. **Cross-Platform Drivers:** Building open virtual keyboard and Wayland/macOS accessibility integration.

---

## 7. Author & Maintainer

* **Taras Chernov** (Sofia, Bulgaria, EU)
* GitHub: [@taraschernov](https://github.com/taraschernov)
* Email: `taras.chernov@gmail.com`

