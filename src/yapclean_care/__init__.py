"""
YapClean Care: Open-Source Assistive Desktop Speech Layer
for Atypical and Dysarthric Voice Input.
"""

from yapclean_care.audio_buffer import DynamicAtypicalVAD, PreRollAudioBuffer
from yapclean_care.cadsr_adapter import (
    CADSRDysarthriaPromptAdapter,
    StandardPromptFilter,
)
from yapclean_care.decoder_config import (
    AcousticDecoderConfig,
    get_sweet_spot_config,
)
from yapclean_care.layout_translator import LayoutTranslator
from yapclean_care.wer_metrics import compute_wer, normalize_for_wer

__version__ = "1.1.0"

__all__ = [
    "PreRollAudioBuffer",
    "DynamicAtypicalVAD",
    "CADSRDysarthriaPromptAdapter",
    "StandardPromptFilter",
    "AcousticDecoderConfig",
    "get_sweet_spot_config",
    "LayoutTranslator",
    "compute_wer",
    "normalize_for_wer",
]

