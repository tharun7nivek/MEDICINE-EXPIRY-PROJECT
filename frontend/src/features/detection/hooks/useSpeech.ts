import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getSpeechLang } from "../../../i18n";
import type { ExpiryStatus } from "../types/detect.types";

export type SpeechErrorCode = "unsupported" | "error";

export interface SpeakResult {
  ok: boolean;
  error?: SpeechErrorCode;
  /** True when no matching voice was found for the current locale. */
  voiceUnavailable?: boolean;
}

function findVoiceForLang(lang: string, localeCode: string): SpeechSynthesisVoice | null {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) {
    return null;
  }

  const voices = window.speechSynthesis.getVoices();
  if (voices.length === 0) return null;

  const exact = voices.find((v) => v.lang === lang || v.lang.replace("_", "-") === lang);
  if (exact) return exact;

  const prefix = voices.find(
    (v) =>
      v.lang.toLowerCase().startsWith(localeCode.toLowerCase()) ||
      v.lang.toLowerCase().startsWith(lang.slice(0, 2).toLowerCase())
  );
  return prefix ?? null;
}

/**
 * Web Speech API wrapper for localized expiry summaries.
 * Cancels any in-flight utterance before speaking again.
 */
export function useSpeech() {
  const { t, i18n } = useTranslation();
  const [isSpeaking, setIsSpeaking] = useState(false);

  const cancel = useCallback(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
  }, []);

  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  // Chrome loads voices asynchronously; warm the cache when language changes.
  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;

    const warm = () => {
      void window.speechSynthesis.getVoices();
    };
    warm();
    window.speechSynthesis.addEventListener("voiceschanged", warm);
    return () => {
      window.speechSynthesis.removeEventListener("voiceschanged", warm);
    };
  }, [i18n.language]);

  const speak = useCallback(
    (text: string): SpeakResult => {
      if (typeof window === "undefined" || !("speechSynthesis" in window)) {
        return { ok: false, error: "unsupported" };
      }

      const localeCode = i18n.language.split("-")[0] ?? "en";
      const lang = getSpeechLang(localeCode);
      const voice = findVoiceForLang(lang, localeCode);
      const voiceUnavailable = voice == null;

      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang;
      if (voice) utterance.voice = voice;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      try {
        window.speechSynthesis.speak(utterance);
        return { ok: true, voiceUnavailable };
      } catch {
        setIsSpeaking(false);
        return { ok: false, error: "error" };
      }
    },
    [i18n.language]
  );

  const speakExpirySummary = useCallback(
    (
      mfg: string | null,
      exp: string | null,
      status: ExpiryStatus,
      needsReview = false
    ): SpeakResult => {
      const mfgPart = mfg
        ? t("speech.mfgFound", { date: mfg })
        : t("speech.mfgMissing");
      const expPart = exp
        ? t("speech.expFound", { date: exp })
        : t("speech.expMissing");

      const statusKey =
        status === "valid"
          ? "speech.statusValid"
          : status === "expired"
            ? "speech.statusExpired"
            : "speech.statusUnknown";

      const reviewPart = needsReview
        ? t("speech.reviewNeeded")
        : t("speech.reviewNotNeeded");

      return speak(`${mfgPart} ${expPart} ${t(statusKey)} ${reviewPart}`);
    },
    [speak, t]
  );

  return {
    speak,
    speakExpirySummary,
    cancel,
    isSpeaking,
  };
}
