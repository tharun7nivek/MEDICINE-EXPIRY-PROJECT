import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";
import hi from "./locales/hi.json";
import ta from "./locales/ta.json";
import te from "./locales/te.json";
import mr from "./locales/mr.json";
import bn from "./locales/bn.json";
import gu from "./locales/gu.json";
import kn from "./locales/kn.json";
import ml from "./locales/ml.json";
import pa from "./locales/pa.json";

export const LANGUAGE_STORAGE_KEY = "medexpiry-lang";

export const SUPPORTED_LANGUAGES = [
  { code: "en", label: "English", speechLang: "en-IN" },
  { code: "hi", label: "हिन्दी", speechLang: "hi-IN" },
  { code: "ta", label: "தமிழ்", speechLang: "ta-IN" },
  { code: "te", label: "తెలుగు", speechLang: "te-IN" },
  { code: "mr", label: "मराठी", speechLang: "mr-IN" },
  { code: "bn", label: "বাংলা", speechLang: "bn-IN" },
  { code: "gu", label: "ગુજરાતી", speechLang: "gu-IN" },
  { code: "kn", label: "ಕನ್ನಡ", speechLang: "kn-IN" },
  { code: "ml", label: "മലയാളം", speechLang: "ml-IN" },
  { code: "pa", label: "ਪੰਜਾਬੀ", speechLang: "pa-IN" },
] as const;

export type LanguageCode = (typeof SUPPORTED_LANGUAGES)[number]["code"];

const resources = {
  en: { translation: en },
  hi: { translation: hi },
  ta: { translation: ta },
  te: { translation: te },
  mr: { translation: mr },
  bn: { translation: bn },
  gu: { translation: gu },
  kn: { translation: kn },
  ml: { translation: ml },
  pa: { translation: pa },
} as const;

function readStoredLanguage(): LanguageCode {
  if (typeof localStorage === "undefined") return "en";
  const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  const match = SUPPORTED_LANGUAGES.find((lang) => lang.code === stored);
  return match?.code ?? "en";
}

export function getSpeechLang(code: string): string {
  const match = SUPPORTED_LANGUAGES.find((lang) => lang.code === code);
  return match?.speechLang ?? "en-IN";
}

export function isSupportedLanguage(code: string): code is LanguageCode {
  return SUPPORTED_LANGUAGES.some((lang) => lang.code === code);
}

const initialLanguage = readStoredLanguage();

void i18n.use(initReactI18next).init({
  resources,
  lng: initialLanguage,
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
});

if (typeof document !== "undefined") {
  document.documentElement.lang = initialLanguage;
}

i18n.on("languageChanged", (lng) => {
  if (isSupportedLanguage(lng)) {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, lng);
  }
  if (typeof document !== "undefined") {
    document.documentElement.lang = lng;
  }
});

export default i18n;
