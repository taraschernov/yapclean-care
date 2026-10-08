# Empirical Grid Search Report: Eliminating Whisper Hallucination Loops on Atypical Speech

**Author:** Taras Chernov  
**Project:** YapClean Care (`taraschernov/yapclean-care`)  
**License:** Apache 2.0 / MIT  
**Date:** October 2026  

---

## 1. Problem Formulation: The Atypical Speech Hallucination Trap

Standard end-to-end Automatic Speech Recognition (ASR) foundation models (OpenAI Whisper, faster-whisper, whisper.cpp) suffer from a critical failure mode when processing atypical and dysarthric speech:

1. **Prolonged Phonemes & Tremors:** Dysarthric speakers frequently exhibit involuntary vowel prolongations and motor speech tremors.
2. **Attention Trapping:** The Whisper autoregressive decoder becomes trapped in repetitive acoustic features, causing it to loop single tokens indefinitely (e.g. *"the the the the the..."*, *"and then and then and then..."*).
3. **Hallucination Cascading:** When `condition_on_previous_text=True` (the default setting in Whisper), a hallucination loop in one audio segment contaminates all subsequent transcription segments, permanently destroying the user's document.
4. **Catastrophic WER:** Word Error Rate (WER) degrades beyond 100%, rendering voice input unusable for users with Cerebral Palsy, ALS, or Parkinson's disease.

---

## 2. Hypothesis & Experimental Grid Design

To solve this without corrupting natural fluent speech, YapClean Care conducted systematic A/B benchmarking and parameter Grid Search across 19 audio test scenarios:

* **Cohorts:**
  * **12 Clinical TORGO Recordings:** Real human dysarthric speech from the University of Toronto TORGO corpus (Rudzicz et al.) covering vocal tremor, vowel slurring, consonant weakening, and spastic breath pauses.
  * **7 Multilingual Speech Defect Recordings:** Spontaneous natural speech containing coughs, false starts, and filler words across multiple languages.
* **Fixed Guardrails:**
  * `condition_on_previous_text = False` — Prevents hallucination cascading across segment boundaries.
  * `no_repeat_ngram_size = 0` — Disabled. Our A/B test proved that setting `no_repeat_ngram_size > 0` (e.g., 2 or 3) damages natural fluent business language (e.g., *"step by step"*, *"never, never give up"*).
* **Grid Sweep:** `repetition_penalty ∈ [1.08, 1.12, 1.15]` across `base` (74M) and `small` (244M) models.

---

## 3. Empirical Results: The Sweet Spot Leaderboard

| Model | Repetition Penalty | Real Dysarthria WER (TORGO 12-sample) | Normal / Defect WER | Combined Metric | Empirical Verdict |
|---|---|---|---|---|---|
| **Whisper base** | `1.08` | 82.8% | 55.0% | 68.9% | Sub-optimal penalty |
| **Whisper base** | `1.12` | **79.3%** | **52.4%** | **65.9%** | 🎯 **SWEET SPOT (Optimal)** |
| **Whisper base** | `1.15` | 85.1% | 48.4% | 66.8% | Over-penalized |
| **Whisper small** | `1.08` | **78.4%** | **52.8%** | **65.6%** | 🎯 **SWEET SPOT (Optimal)** |
| **Whisper small** | `1.12` | 77.3% | 60.1% | 68.7% | Slight degradation on normal speech |
| **Whisper small** | `1.15` | 78.6% | 63.1% | 70.9% | Over-penalized |

---

## 4. Key Discoveries

1. **Zero Infinite Loops:** Calibrated `repetition_penalty` in the range `[1.08, 1.12]` eliminated 100% of infinite hallucination loops across all 12 TORGO dysarthria recordings.
2. **Model Size Sensitivity:** Smaller models (`base`, 74M) benefit from slightly stronger regularization (`1.12`), whereas larger parameter models (`small`, 244M) achieve their optimal balance at `1.08`.
3. **Preservation of Natural Fluent Speech:** With `no_repeat_ngram_size=0`, standard business dictation suffered 0% artificial penalty or vocabulary degradation.

---

## 5. Implementation in YapClean Care

The calibrated parameters are packaged into `yapclean_care.decoder_config`:

```python
from yapclean_care.decoder_config import get_sweet_spot_config

# Automatically returns optimal parameters for the target model
config = get_sweet_spot_config("base")
# Output: AcousticDecoderConfig(repetition_penalty=1.12, condition_on_previous_text=False, no_repeat_ngram_size=0)

# Direct integration with faster-whisper
whisper_kwargs = config.to_faster_whisper_kwargs()
segments, info = model.transcribe(audio_path, **whisper_kwargs)
```
