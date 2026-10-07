"""
Keyboard Layout Auto-Translation Module for YapClean Care.

Automatically detects the foreground window's active keyboard layout
and translates normalized speech into the target application's language
in real time, eliminating manual layout switching and cognitive fatigue.
"""

from __future__ import annotations

import sys
from typing import Optional


# Mapping of Win32 Primary Language IDs to ISO 639-1 language codes
WIN32_LANG_MAP: dict[int, str] = {
    0x09: "en",  # English
    0x19: "ru",  # Russian
    0x02: "bg",  # Bulgarian
    0x22: "uk",  # Ukrainian
    0x07: "de",  # German
    0x0C: "fr",  # French
    0x10: "it",  # Italian
    0x0A: "es",  # Spanish
    0x15: "pl",  # Polish
}


class LayoutTranslator:
    """Manages active OS keyboard layout detection and live text translation."""

    def __init__(self, default_target_lang: str = "en") -> None:
        self.default_target_lang = default_target_lang

    def get_active_layout_lang(self) -> str:
        """Detect the keyboard layout language of the currently active foreground window.
        
        Returns:
            ISO 639-1 language code (e.g., 'en', 'ru', 'bg'), or default if undetectable.
        """
        if sys.platform != "win32":
            return self.default_target_lang

        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return self.default_target_lang

            thread_id = user32.GetWindowThreadProcessId(hwnd, 0)
            layout_id = user32.GetKeyboardLayout(thread_id)
            # Low word is the language identifier
            lang_id = layout_id & 0xFFFF
            primary_lang_id = lang_id & 0x3FF
            return WIN32_LANG_MAP.get(primary_lang_id, self.default_target_lang)
        except Exception:
            return self.default_target_lang

    def should_translate(self, dictation_lang: str, active_layout_lang: Optional[str] = None) -> bool:
        """Check if dictation language differs from the active layout language.
        
        Args:
            dictation_lang: Language code of the user's spoken input.
            active_layout_lang: Target language code (auto-detected if None).
            
        Returns:
            True if translation is required; False otherwise.
        """
        target = active_layout_lang or self.get_active_layout_lang()
        d_code = (dictation_lang or "").strip().lower().split("-")[0]
        t_code = (target or "").strip().lower().split("-")[0]
        return bool(d_code and t_code and d_code != t_code)

    def format_translation_prompt(self, text: str, source_lang: str, target_lang: str) -> str:
        """Construct a high-fidelity translation prompt preserving spoken tone.
        
        Args:
            text: Normalized text to translate.
            source_lang: Spoken input language.
            target_lang: Destination layout language.
            
        Returns:
            Instruction prompt for language model or translation API.
        """
        return (
            f"Translate the following spoken text directly from {source_lang} to {target_lang}. "
            f"Preserve casual conversational tone, technical terms, and punctuation. "
            f"Output ONLY the translated text without commentary or quotes:\n\n{text}"
        )
