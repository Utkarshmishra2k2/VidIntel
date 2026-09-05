"""
Lightweight heuristic language & tone detection for English / Hindi / Hinglish.

This is intentionally simple (keyword + script based) rather than a full
language-ID model, because the only thing it needs to decide is which system
prompt / response style to use. There is exactly one copy of this logic in
the codebase — do not duplicate it elsewhere.
"""
import re
from typing import Literal, TypedDict

from app.utils.logging import logger

Language = Literal["English", "Hindi", "Hinglish"]
Tone = Literal["neutral", "casual"]


class LanguageInfo(TypedDict):
    language: Language
    tone: Tone


_CASUAL_KEYWORDS = {
    "bro", "dude", "bhai", "yaar", "pls", "plz", "quick", "fast",
    "lol", "haha", "wtf", "omg", "boss", "king", "chill",
}

_ROMAN_HINDI_KEYWORDS = {
    "bhai", "yaar", "kya", "mein", "hai", "tha", "hui", "kar",
    "raha", "batao", "batayo", "samjha", "kaise", "kyun", "nahi",
}

_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_WORD_RE = re.compile(r"[a-zA-Z']+")


def detect_language_and_tone(text: str) -> LanguageInfo:
    text = (text or "").strip()
    if not text:
        return {"language": "English", "tone": "neutral"}

    words = set(w.lower() for w in _WORD_RE.findall(text))
    has_devanagari = bool(_DEVANAGARI_RE.search(text))
    has_roman_hindi = bool(words & _ROMAN_HINDI_KEYWORDS)
    is_casual = bool(words & _CASUAL_KEYWORDS)

    if has_devanagari:
        language: Language = "Hindi"
    elif has_roman_hindi:
        language = "Hinglish"
    else:
        language = "English"

    tone: Tone = "casual" if (is_casual or language != "English") else "neutral"

    logger.debug(f"Language detection -> language={language}, tone={tone}")
    return {"language": language, "tone": tone}
