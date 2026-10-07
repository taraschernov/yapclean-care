# Empirical Multilingual Audio Benchmark & Slavic Adaptation Strategy

## 1. Multilingual Audio Benchmark Results (25 Test Scenarios)

To evaluate speech cleaning and reconstruction across diverse linguistic and acoustic conditions, YapClean deployed an automated benchmark harness testing 25 calibrated audio test cases across 5 languages:
* **Languages Tested:** Russian (RU), Ukrainian (UK), English (EN), German (DE), Spanish (ES).
* **Audio Synthesis:** Synthesized using **Google Gemini 3.8 Flash-Lite TTS** at studio-quality 24 kHz, embedding calibrated human speech defects: coughs (`<cough>`), audible breathing (`<breath>`), sighs (`<sigh>`), false starts, and filler words.
* **Acoustic Transcriber:** Groq Whisper Large v3.

### 1.1. Overall Engine Leaderboard

| Rank | Cleaning Engine | Architecture | Cases Passed | Pass Rate | Average Latency | Cost / Mode |
|---|---|---|---|---|---|---|
| **🥇 1** | **Groq Llama 3.3 70B** | Cloud LLM (LPU) | **20 / 25** | **80.0%** | **299 ms** | Cloud API |
| **🥈 2** | **Groq Llama 3.1 8B** | Cloud LLM (LPU) | **20 / 25** | **80.0%** | **321 ms** | Cloud API |
| **🥉 3** | **Gemini 2.5 Flash** | Multimodal Cloud | **17 / 25** | **68.0%** | **3,748 ms** | Cloud API |
| **4** | **YapClean Local Rules** | Deterministic Local Engine | **15 / 25** | **60.0%** | **0 ms** | **100% Offline / $0** |

### 1.2. Breakdown by Speech Defect Category

| Defect Category | Description | Groq Llama 70B | Groq Llama 8B | Gemini 2.5 Flash | YapClean Local Rules |
|---|---|---|---|---|---|
| **`hesitation`** | Self-corrections & false starts | **5/5 (100%)** | **5/5 (100%)** | **5/5 (100%)** | **5/5 (100%)** |
| **`cleanliness`** | Acoustic noise, coughs, sighs | **5/5 (100%)** | **5/5 (100%)** | **5/5 (100%)** | **5/5 (100%)** |
| **`fillers`** | Filler words ("you know", "like", "ну") | **5/5 (100%)** | **5/5 (100%)** | 3/5 (60%) | 1/5 (20%) |
| **`zero_distortion`** | Technical brand preservation | 3/5 (60%) | 3/5 (60%) | 3/5 (60%) | 3/5 (60%) |
| **`structure`** | Multi-clause syntax & punctuation | 2/5 (40%) | 2/5 (40%) | 1/5 (20%) | 1/5 (20%) |

**Key Takeaways:**
1. **100% Universal Pass on Self-Corrections & Acoustic Noise:** Every evaluated engine—including the zero-cost local rule engine—achieved 100% accuracy in removing false starts and cough/throat-clearing artifacts.
2. **Sub-350ms Real-Time Performance:** Groq LPU inference enables real-time normalization within 300 ms, imperceptible to the human speaker.
3. **Zero-Latency Local Fallback:** YapClean's standalone local engine delivers 60% accuracy with literally 0 ms latency, guaranteeing basic functionality even completely offline.

---

## 2. Google Project Euphonia Analysis & The Slavic Language Gap

### 2.1. What Google's Research Proved (Project Euphonia & Project Relate)
In seminal publications (*MacDonald et al., Google Research, Interspeech 2021; Green et al., ICASSP 2021*), Google demonstrated that standard BigTech ASR fails on non-standard speech, but can be adapted:
* Google collected over **1,000,000 non-standard speech utterances** (~1,400 hours) across individuals with ALS, Cerebral Palsy, Parkinson's disease, and stroke.
* **Critical Finding:** Fine-tuning an end-to-end ASR model on as little as **30 minutes of speaker-specific atypical speech** yields a **35% relative reduction in Word Error Rate (WER)**.

### 2.2. The Critical Limitation: Euphonia is Closed and English-Only
Despite Google's impressive corpus size:
1. **Data Access Barrier:** The 1M+ utterance Euphonia dataset is proprietary and strictly closed to outside European researchers and independent developers.
2. **Monolingual Focus:** Google's clinical collection is almost exclusively **English**. Public clinical atypical speech corpora for Slavic and Eastern European languages (Bulgarian, Ukrainian, Polish, Czech) **do not exist**.

### 2.3. How YapClean Care Solves the Slavic Gap (Milestone 2 Strategy)
Rather than requiring a million hours of proprietary audio, YapClean Care implements a three-pronged transfer learning strategy:

1. **Multilingual Foundation Encoder Transfer:**
   Models such as `faster-whisper-distil-large-v3` and `nvidia-parakeet-tdt` are pre-trained on tens of thousands of hours of standard multilingual speech. Their internal acoustic feature representations already understand Slavic phonemes (e.g., palatalized consonants, Cyrillic phonetic structures).

2. **Cyrillic CADSR-LM Semantic Normalization:**
   Instead of retraining the entire acoustic model from scratch, CADSR-LM acts as a semantic post-processor. It applies Cyrillic phonetic homophone mappings to dynamically reconstruct slurred consonants (e.g. Bulgarian/Russian/Ukrainian specific consonant clusters) using linguistic context without hallucinating.

3. **Synthetic Acoustic Perturbation Calibration:**
   Leveraging our reproducible audio generator (Gemini 3.8 Flash-Lite TTS), we generate synthetic Slavic atypical speech datasets by programmatically injecting tremors, prolonged vowels, and spastic hesitations. This allows systematic benchmark calibration of local offline models without burdening vulnerable clinical patients.

4. **Community Co-Design Calibration (Milestone 4):**
   In collaboration with accessibility volunteers in Bulgaria and Ukraine, we collect targeted 15-minute calibration recordings to validate and fine-tune open lightweight models for zero-cloud, 100% private offline dictation.
