import { useTranslation } from "react-i18next";
import { Languages } from "lucide-react";
import {
  SUPPORTED_LANGUAGES,
  type LanguageCode,
  isSupportedLanguage,
} from "../../i18n";

/**
 * Language switcher backed by i18next; preference persists via i18n languageChanged.
 */
export default function LanguageSwitcher() {
  const { t, i18n } = useTranslation();

  const current: LanguageCode = isSupportedLanguage(i18n.language)
    ? i18n.language
    : "en";

  const onChange = (code: LanguageCode) => {
    void i18n.changeLanguage(code);
  };

  return (
    <label className="relative inline-flex items-center gap-1.5 text-sm text-[var(--color-ink)]">
      <Languages
        className="size-4 shrink-0 text-[var(--color-teal-700)]"
        aria-hidden
      />
      <span className="sr-only">{t("nav.language")}</span>
      <select
        value={current}
        onChange={(e) => onChange(e.target.value as LanguageCode)}
        className="max-w-[9.5rem] cursor-pointer appearance-none rounded-md border border-teal-800/15 bg-white/70 py-1.5 pl-2 pr-7 text-sm text-[var(--color-ink)] outline-none backdrop-blur-sm transition hover:border-teal-700/30 focus:border-[var(--color-teal-600)] focus:ring-2 focus:ring-teal-600/20"
        aria-label={t("nav.selectLanguage")}
      >
        {SUPPORTED_LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.label}
          </option>
        ))}
      </select>
      <span
        className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-[var(--color-muted)]"
        aria-hidden
      >
        ▾
      </span>
    </label>
  );
}
