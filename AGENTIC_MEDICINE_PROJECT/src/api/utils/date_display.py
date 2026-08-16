"""
Locale-specific pack-date display strings for UI and TTS.

Month names are tables (not OS locales) so Windows servers without Indic
locale packs still format Tamil, Telugu, etc. correctly.
"""

from __future__ import annotations

from src.api.utils.pack_date_parser import ParsedPackDate

SUPPORTED_DISPLAY_LANGS = (
    "en",
    "hi",
    "ta",
    "te",
    "mr",
    "bn",
    "gu",
    "kn",
    "ml",
    "pa",
)

# Index 0 unused; 1–12 are calendar months.
_MONTH_NAMES: dict[str, tuple[str, ...]] = {
    "en": (
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
    "hi": (
        "",
        "जनवरी",
        "फ़रवरी",
        "मार्च",
        "अप्रैल",
        "मई",
        "जून",
        "जुलाई",
        "अगस्त",
        "सितंबर",
        "अक्टूबर",
        "नवंबर",
        "दिसंबर",
    ),
    "ta": (
        "",
        "ஜனவரி",
        "பிப்ரவரி",
        "மார்ச்",
        "ஏப்ரல்",
        "மே",
        "ஜூன்",
        "ஜூலை",
        "ஆகஸ்ட்",
        "செப்டம்பர்",
        "அக்டோபர்",
        "நவம்பர்",
        "டிசம்பர்",
    ),
    "te": (
        "",
        "జనవరి",
        "ఫిబ్రవరి",
        "మార్చి",
        "ఏప్రిల్",
        "మే",
        "జూన్",
        "జూలై",
        "ఆగస్టు",
        "సెప్టెంబర్",
        "అక్టోబర్",
        "నవంబర్",
        "డిసెంబర్",
    ),
    "mr": (
        "",
        "जानेवारी",
        "फेब्रुवारी",
        "मार्च",
        "एप्रिल",
        "मे",
        "जून",
        "जुलै",
        "ऑगस्ट",
        "सप्टेंबर",
        "ऑक्टोबर",
        "नोव्हेंबर",
        "डिसेंबर",
    ),
    "bn": (
        "",
        "জানুয়ারি",
        "ফেব্রুয়ারি",
        "মার্চ",
        "এপ্রিল",
        "মে",
        "জুন",
        "জুলাই",
        "আগস্ট",
        "সেপ্টেম্বর",
        "অক্টোবর",
        "নভেম্বর",
        "ডিসেম্বর",
    ),
    "gu": (
        "",
        "જાન્યુઆરી",
        "ફેબ્રુઆરી",
        "માર્ચ",
        "એપ્રિલ",
        "મે",
        "જૂન",
        "જુલાઈ",
        "ઑગસ્ટ",
        "સપ્ટેમ્બર",
        "ઑક્ટોબર",
        "નવેમ્બર",
        "ડિસેમ્બર",
    ),
    "kn": (
        "",
        "ಜನವರಿ",
        "ಫೆಬ್ರವರಿ",
        "ಮಾರ್ಚ್",
        "ಏಪ್ರಿಲ್",
        "ಮೇ",
        "ಜೂನ್",
        "ಜುಲೈ",
        "ಆಗಸ್ಟ್",
        "ಸೆಪ್ಟೆಂಬರ್",
        "ಅಕ್ಟೋಬರ್",
        "ನವೆಂಬರ್",
        "ಡಿಸೆಂಬರ್",
    ),
    "ml": (
        "",
        "ജനുവരി",
        "ഫെബ്രുവരി",
        "മാർച്ച്",
        "ഏപ്രിൽ",
        "മെയ്",
        "ജൂൺ",
        "ജൂലൈ",
        "ഓഗസ്റ്റ്",
        "സെപ്റ്റംബർ",
        "ഒക്ടോബർ",
        "നവംബർ",
        "ഡിസംബർ",
    ),
    "pa": (
        "",
        "ਜਨਵਰੀ",
        "ਫਰਵਰੀ",
        "ਮਾਰਚ",
        "ਅਪ੍ਰੈਲ",
        "ਮਈ",
        "ਜੂਨ",
        "ਜੁਲਾਈ",
        "ਅਗਸਤ",
        "ਸਤੰਬਰ",
        "ਅਕਤੂਬਰ",
        "ਨਵੰਬਰ",
        "ਦਸੰਬਰ",
    ),
}


def normalize_display_lang(lang: str | None) -> str:
    """Map ``ta``, ``ta-IN``, ``TA`` → ``ta``; unknown → ``en``."""
    if not lang:
        return "en"
    code = lang.strip().replace("_", "-").split("-")[0].lower()
    return code if code in _MONTH_NAMES else "en"


def format_pack_date_display(
    parsed: ParsedPackDate | None,
    lang: str | None = "en",
) -> str | None:
    """
    Render a parsed pack date as a locale month-name string for UI and TTS.

    Month precision: ``ஏப்ரல் 2024``
    Day precision: ``15 ஏப்ரல் 2024``
    """
    if parsed is None:
        return None
    code = normalize_display_lang(lang)
    month_name = _MONTH_NAMES[code][parsed.month]
    if parsed.precision == "day":
        return f"{parsed.day} {month_name} {parsed.year}"
    return f"{month_name} {parsed.year}"
