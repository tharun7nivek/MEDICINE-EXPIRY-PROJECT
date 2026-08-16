"""
speech_templates.py
-------------------
Server-owned spoken expiry summaries (one paragraph per language).
"""

from __future__ import annotations

from src.api.schemas.expiry_assessment import ExpiryStatus
from src.api.utils.date_display import normalize_display_lang

TEMPLATE_VERSION = "v1"

_STATUS: dict[str, dict[str, str]] = {
    "en": {
        "valid": "The medicine is not expired.",
        "expired": "The medicine has expired.",
        "unknown": "The expiry status could not be determined.",
    },
    "hi": {
        "valid": "दवा समाप्त नहीं हुई है।",
        "expired": "दवा की अवधि समाप्त हो चुकी है।",
        "unknown": "समाप्ति स्थिति निर्धारित नहीं हो सकी।",
    },
    "ta": {
        "valid": "மருந்து காலாவதியாகவில்லை.",
        "expired": "மருந்து காலாவதியாகிவிட்டது.",
        "unknown": "காலாவதி நிலையைத் தீர்மானிக்க முடியவில்லை.",
    },
    "te": {
        "valid": "మందు గడువు ముగియలేదు.",
        "expired": "మందు గడువు ముగిసింది.",
        "unknown": "గడువు స్థితిని నిర్ధారించలేకపోయాం.",
    },
    "mr": {
        "valid": "औषध कालबाह्य नाही.",
        "expired": "औषध कालबाह्य झाले आहे.",
        "unknown": "कालबाह्यता स्थिती ठरवता आली नाही.",
    },
    "bn": {
        "valid": "ওষুধ মেয়াদোত্তীর্ণ নয়।",
        "expired": "ওষুধের মেয়াদ শেষ হয়ে গেছে।",
        "unknown": "মেয়াদোত্তীর্ণের অবস্থা নির্ধারণ করা যায়নি।",
    },
    "gu": {
        "valid": "દવા સમાપ્ત નથી.",
        "expired": "દવાની મુદત પૂરી થઈ ગઈ છે.",
        "unknown": "સમાપ્તિ સ્થિતિ નક્કી કરી શકાઈ નથી.",
    },
    "kn": {
        "valid": "ಔಷಧದ ಅವಧಿ ಮುಗಿದಿಲ್ಲ.",
        "expired": "ಔಷಧದ ಅವಧಿ ಮುಗಿದಿದೆ.",
        "unknown": "ಅವಧಿ ಸ್ಥಿತಿಯನ್ನು ನಿರ್ಧರಿಸಲಾಗಲಿಲ್ಲ.",
    },
    "ml": {
        "valid": "മരുന്ന് കാലഹരണപ്പെട്ടിട്ടില്ല.",
        "expired": "മരുന്നിന്റെ കാലാവധി കഴിഞ്ഞു.",
        "unknown": "കാലാവധി നില നിർണയിക്കാനായില്ല.",
    },
    "pa": {
        "valid": "ਦਵਾਈ ਦੀ ਮਿਆਦ ਖਤਮ ਨਹੀਂ ਹੋਈ।",
        "expired": "ਦਵਾਈ ਦੀ ਮਿਆਦ ਖਤਮ ਹੋ ਚੁੱਕੀ ਹੈ।",
        "unknown": "ਮਿਆਦ ਸਥਿਤੀ ਨਿਰਧਾਰਿਤ ਨਹੀਂ ਹੋ ਸਕੀ।",
    },
}

_MFG: dict[str, tuple[str, str]] = {
    "en": ("Manufacturing date {date}.", "Manufacturing date not found."),
    "hi": ("निर्माण तिथि {date}।", "निर्माण तिथि नहीं मिली।"),
    "ta": ("உற்பத்தி தேதி {date}.", "உற்பத்தி தேதி கிடைக்கவில்லை."),
    "te": ("తయారీ తేదీ {date}.", "తయారీ తేదీ కనుగొనబడలేదు."),
    "mr": ("निर्मिती तारीख {date}.", "निर्मिती तारीख सापडली नाही."),
    "bn": ("উৎপাদনের তারিখ {date}।", "উৎপাদনের তারিখ পাওয়া যায়নি।"),
    "gu": ("ઉત્પાદન તારીખ {date}.", "ઉત્પાદન તારીખ મળી નથી."),
    "kn": ("ತಯಾರಿಕೆ ದಿನಾಂಕ {date}.", "ತಯಾರಿಕೆ ದಿನಾಂಕ ಸಿಗಲಿಲ್ಲ."),
    "ml": ("നിർമ്മാണ തീയതി {date}.", "നിർമ്മാണ തീയതി കണ്ടെത്തിയില്ല."),
    "pa": ("ਨਿਰਮਾਣ ਤਾਰੀਖ {date}।", "ਨਿਰਮਾਣ ਤਾਰੀਖ ਨਹੀਂ ਮਿਲੀ।"),
}

_EXP: dict[str, tuple[str, str]] = {
    "en": ("Expiry date {date}.", "Expiry date not found."),
    "hi": ("समाप्ति तिथि {date}।", "समाप्ति तिथि नहीं मिली।"),
    "ta": ("காலாவதி தேதி {date}.", "காலாவதி தேதி கிடைக்கவில்லை."),
    "te": ("గడువు తేదీ {date}.", "గడువు తేదీ కనుగొనబడలేదు."),
    "mr": ("कालबाह्यता तारीख {date}.", "कालबाह्यता तारीख सापडली नाही."),
    "bn": ("মেয়াদোত্তীর্ণের তারিখ {date}।", "মেয়াদোত্তীর্ণের তারিখ পাওয়া যায়নি।"),
    "gu": ("સમાપ્તિ તારીખ {date}.", "સમાપ્તિ તારીખ મળી નથી."),
    "kn": ("ಅವಧಿ ಮುಗಿಯುವ ದಿನಾಂಕ {date}.", "ಅವಧಿ ಮುಗಿಯುವ ದಿನಾಂಕ ಸಿಗಲಿಲ್ಲ."),
    "ml": ("കാലാവധി തീയതി {date}.", "കാലാവധി തീയതി കണ്ടെത്തിയില്ല."),
    "pa": ("ਮਿਆਦ ਖਤਮ ਹੋਣ ਦੀ ਤਾਰੀਖ {date}।", "ਮਿਆਦ ਖਤਮ ਹੋਣ ਦੀ ਤਾਰੀਖ ਨਹੀਂ ਮਿਲੀ।"),
}

_REVIEW: dict[str, tuple[str, str]] = {
    "en": ("This result needs human review.", "Human review is not required."),
    "hi": ("इस परिणाम की मानव समीक्षा आवश्यक है।", "मानव समीक्षा आवश्यक नहीं है।"),
    "ta": ("இந்த முடிவுக்கு மனித மதிப்பாய்வு தேவை.", "மனித மதிப்பாய்வு தேவையில்லை."),
    "te": ("ఈ ఫలితానికి మానవ సమీక్ష అవసరం.", "మానవ సమీక్ష అవసరం లేదు."),
    "mr": ("या निकालासाठी मानवी समीक्षा आवश्यक आहे.", "मानवी समीक्षा आवश्यक नाही."),
    "bn": ("এই ফলাফলের মানব পর্যালোচনা প্রয়োজন।", "মানব পর্যালোচনা প্রয়োজন নেই।"),
    "gu": ("આ પરિણામની માનવ સમીક્ષા જરૂરી છે.", "માનવ સમીક્ષા જરૂરી નથી."),
    "kn": ("ಈ ಫಲಿತಾಂಶಕ್ಕೆ ಮಾನವ ವಿಮರ್ಶೆ ಅಗತ್ಯವಿದೆ.", "ಮಾನವ ವಿಮರ್ಶೆ ಅಗತ್ಯವಿಲ್ಲ."),
    "ml": ("ഈ ഫലത്തിന് മനുഷ്യ അവലോകനം വേണം.", "മനുഷ്യ അവലോകനം വേണ്ട."),
    "pa": ("ਇਸ ਨਤੀਜੇ ਲਈ ਮਨੁੱਖੀ ਸਮੀਖਿਆ ਲੋੜੀਂਦੀ ਹੈ।", "ਮਨੁੱਖੀ ਸਮੀਖਿਆ ਲੋੜੀਂਦੀ ਨਹੀਂ ਹੈ।"),
}


def render_expiry_summary(
    lang: str | None,
    expiry_status: ExpiryStatus,
    mfg_display: str | None,
    exp_display: str | None,
    needs_human_review: bool,
) -> tuple[str, str]:
    """
    Return ``(normalized_lang, spoken_paragraph)``.
    """
    code = normalize_display_lang(lang)
    status_line = _STATUS[code][expiry_status]
    mfg_found, mfg_missing = _MFG[code]
    exp_found, exp_missing = _EXP[code]
    review_needed, review_clear = _REVIEW[code]

    mfg_line = (
        mfg_found.format(date=mfg_display.strip())
        if mfg_display and mfg_display.strip()
        else mfg_missing
    )
    exp_line = (
        exp_found.format(date=exp_display.strip())
        if exp_display and exp_display.strip()
        else exp_missing
    )
    review_line = review_needed if needs_human_review else review_clear
    paragraph = " ".join((status_line, mfg_line, exp_line, review_line))
    return code, paragraph
