# YapClean Care: Open-Source Assistive Desktop Speech Layer
### High-Fidelity Voice Input & Normalization for Atypical, Dysarthric, and Multilingual Speech

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-24%2F24%20Passing-success.svg)](tests/)
[![Atypical Speech Benchmark](https://img.shields.io/badge/TORGO%20Benchmark-12%20Clinical%20Samples-brightgreen.svg)](tests/samples/manifest.json)
[![Sweet Spot Grid Search](https://img.shields.io/badge/ASR%20Decoder-Sweet%20Spot%20Calibrated-success.svg)](docs/GRID_SEARCH_SWEET_SPOT_REPORT.md)
[![Multilingual Audio Benchmark](https://img.shields.io/badge/Audio%20Benchmark-25%20Cases%20%7C%205%20Languages-blue.svg)](docs/MULTILINGUAL_AUDIO_BENCHMARK_REPORT.md)
[![Competitive Audit](https://img.shields.io/badge/Competitive%20Audit-Zero%20Dark%20Patterns-purple.svg)](docs/COMPETITIVE_ANALYSIS_AND_DIFFERENTIATION.md)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-ea4aaa?logo=github&style=flat)](https://github.com/sponsors/taraschernov)
[![Open Collective](https://img.shields.io/badge/Open%20Collective-Donate-blue?logo=open-collective&style=flat)](https://opencollective.com/yapclean-care)
[![Polar.sh](https://img.shields.io/badge/Polar.sh-Fund%20Bounties-0052FF?logo=polar&style=flat)](https://polar.sh/taraschernov)

---

> **Status (2026-11-04) - please read.** This repository is a small Python library plus tests and
> measurements, not a finished assistive product. An audit of our own earlier text found claims that
> are wrong or unproven (an invented "71.8% -> 0.0% WER" result, whisper.cpp/Linux/macOS/HID
> support that does not exist, no screen-reader testing). The full list, what is real, what is
> not solved and what funding would be for: [docs/STATUS.md](docs/STATUS.md).
> The story of how the error happened and was found, with the real picture:
> [docs/INVESTIGATION_2026-11-04.md](docs/INVESTIGATION_2026-11-04.md).
> Care mode itself runs in the proprietary YapClean Windows app; the numbers below come from it.
> Most of the code and documents here were written with AI coding assistants (Anthropic Claude, Google Gemini) under the maintainer's direction.

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

### 2.1. TORGO Clinical Dataset (Zero-Shot Atypical Speech Benchmark)

Evaluated on 12 real clinical dysarthric speech recordings from the open **TORGO Database** (University of Toronto; Rudzicz et al., speakers with cerebral palsy and ALS reading the 1916 phonetic stress-test *"The Grandfather Passage"*). 

> **Correction (2026-10-29).** An independent re-run on the same 12 recordings
> (production `whisper-large-v3` on Groq, current Care pipeline, our own WER code)
> shows where the gain over the uncalibrated baseline comes from: the stronger
> recognition model and the guardrails that stop hallucination loops and
> foreign-script output. The LLM cleanup layer itself does **not** lower WER on
> dysarthric speech (61.0% raw recognition vs 61.4% after Care cleanup). Other
> engines were not better on this set (Deepgram nova-3 63.5%, Gemini audio 70.7%).
> Twelve samples are too few for strong conclusions. Details:
> [docs/TORGO_CARE_MODE_BENCHMARK.md](docs/TORGO_CARE_MODE_BENCHMARK.md#independent-re-run-and-correction-2026-10-29).

The rows below come from runs on real audio (the rule-based helper in this repository was not involved). Only the cloud column was re-run independently; the individual clips shown are examples, not a representative sample. Cite the averages in the correction above, not this table:

| Metric / Scenario | Default Whisper Small (Uncalibrated) | YapClean Calibrated Local (Small, `rep_pen=1.08`) | YapClean Cloud Care Mode (`whisper-large-v3` + Llama 3.3 70B) |
|---|---|---|---|
| **Average Word Error Rate (WER)** | **110.8%** (Severe loop collapse) | **64.6%** (Stable decode) | **59.8%** (Clinical baseline limit) |
| **Spastic Pause Loops (`0012`)** | ❌ **350.0% WER** (130+ hallucinated tokens) | ✅ **100.0% WER** (0 looping) | ✅ **87.5% WER** (Loop-free semantic capture) |
| **Foreign Script Hallucination (`0026`)**| ❌ **587.5% WER** (Telugu script hallucination) | ✅ **100.0% WER** (Noise suppressed) | ✅ **50.0% WER** (*"He still thinks as swiftly as ever"*) |
| **Moderate Dysarthria (`0053`)** | 62.5% WER | 25.0% WER | 🎯 **12.5% WER** (*"You wish to know all about my grandfather"*) |
| **Non-Linear Consonant Weakening (`0019`)**| ❌ 177.8% WER (*"plugin usc conference"*) | 55.6% WER | 🎯 **33.3% WER** (*"He dressed himself in an Asian black frog coat"*) |
| **Hallucination Loop Suppression** | 0% (Runaway repetitions on pauses) | **100% Loop Elimination** | **100% Loop Elimination** |

📄 **Full Scientific & Engineering Report:** [`docs/TORGO_CARE_MODE_BENCHMARK.md`](docs/TORGO_CARE_MODE_BENCHMARK.md)  
📊 **Raw Benchmark Datasets:** [`benchmarks/data/honest_benchmark_results.json`](benchmarks/data/honest_benchmark_results.json) & [`benchmarks/data/groq_whisper_large_care_results.json`](benchmarks/data/groq_whisper_large_care_results.json)

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

## 3. Target architecture (NOT fully built; status table first)

| Item | Status |
|---|---|
| Hotkey-toggled recording, typing into any Windows app, cleanup guardrails, tuned decoding, layout detection | **Built** (in the YapClean app; guardrail and decoder code published here) |
| Pre-roll buffer and pause-tolerant VAD | **Library classes only**, tested on synthetic arrays, not wired into an app |
| Offline `whisper.cpp` tier, <500 MB RAM, <30 ms latency | **Not built / never measured** |
| Tier 3 relay, NGO/clinic vouchers, partners | **Not built** |
| Switch, sip-and-puff, foot-pedal support; earcons | **Not built** |
| Linux and macOS | **Not built** (Windows x64 only) |
| Screen-reader coexistence (`WS_EX_NOACTIVATE`) | **Unverified**, never tested with NVDA/JAWS |

The diagram below is the design we aim for, not a description of shipped software.

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

### 3.3. Assistive Hardware Interface (Open HID) - NOT IMPLEMENTED
Planned to be compatible with physical accessibility switches, sip-and-puff controllers, and USB foot pedals, enabling fully hands-free desktop dictation for quadriplegic and motor-impaired individuals.

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
# Run the unit tests (rule-based helper, guardrails, decoder config, buffer/VAD classes)
pytest tests/ -v
```

Expected: `24 passed`. These tests check code behaviour on hand-written strings; they are not a
recognition benchmark. Real-audio measurements are in `docs/TORGO_CARE_MODE_BENCHMARK.md`.

---

## 5. European accessibility context

* **European Accessibility Act (Directive 2019/882):** Built to empower public and private sector employers to satisfy accessibility workplace obligations.
* **Permissive Open-Source Licensing:** Released under **Apache-2.0 OR MIT** (see `LICENSE` and `LICENSE-MIT`).

---

## 6. Community Funding & Sustainability (Sponsorship)

YapClean Care is an independent digital public good released under Apache-2.0 OR MIT. To ensure sustainable open-source development, long-term maintenance, and infrastructure subsidies for vulnerable users, we welcome recurring and one-time sponsorships:

| Platform | Best For | Details & Transparency |
|---|---|---|
| [**GitHub Sponsors**](https://github.com/sponsors/taraschernov) | Individuals & Developers | 0% transaction fees for individual contributions; recurring monthly or one-time micro-support. |
| [**Open Collective**](https://opencollective.com/yapclean-care) | Companies & Foundations | Transparent fiscal hosting with publicly auditable expenses, invoices, and corporate tax receipts. |
| [**Polar.sh**](https://polar.sh/taraschernov) | Feature Bounties | Pledge bounties directly to specific issues, Linux Wayland drivers, or benchmark datasets. |

### How Sponsorship Funds Would Be Allocated (planned; none of this exists yet):
1. **At-Cost Accessibility Subsidies:** Funding API allowances for quadriplegic and dysarthric users on legacy hardware who cannot run heavy on-device neural models.
2. **Open Clinical Datasets:** Curating, annotating, and benchmarking atypical speech samples across underrepresented European languages.
3. **Cross-Platform Drivers:** Building open virtual keyboard and Wayland/macOS accessibility integration.

---

## 7. Author & Maintainer

* **Taras Chernov** (Sofia, Bulgaria, EU)
* GitHub: [@taraschernov](https://github.com/taraschernov)
* Email: `taras.chernov@gmail.com`

