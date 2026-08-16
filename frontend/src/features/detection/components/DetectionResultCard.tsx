import { useTranslation } from "react-i18next";
import { Square, Volume2 } from "lucide-react";
import type { DetectResponse, ExpiryStatus } from "../types/detect.types";

const STATUS_CLASS: Record<ExpiryStatus, string> = {
  valid:
    "bg-[var(--color-ok-soft)] text-[var(--color-ok)] ring-1 ring-emerald-700/15",
  expired:
    "bg-[var(--color-danger-soft)] text-[var(--color-danger)] ring-1 ring-red-700/15",
  unknown:
    "bg-[var(--color-warn-soft)] text-[var(--color-warn)] ring-1 ring-amber-700/15",
};

const REVIEW_CLASS = {
  needed:
    "bg-[var(--color-warn-soft)] text-[var(--color-warn)] ring-1 ring-amber-700/15",
  clear:
    "bg-[var(--color-ok-soft)] text-[var(--color-ok)] ring-1 ring-emerald-700/15",
} as const;

export interface DetectionResultCardProps {
  result: DetectResponse;
  onListen: () => void;
  onStopSpeech: () => void;
  isSpeaking?: boolean;
  isLoadingSpeech?: boolean;
}

export default function DetectionResultCard({
  result,
  onListen,
  onStopSpeech,
  isSpeaking = false,
  isLoadingSpeech = false,
}: DetectionResultCardProps) {
  const { t } = useTranslation();
  const { expiry_status, needs_human_review } = result.assessment;

  const titleKey =
    expiry_status === "valid"
      ? "result.titleValid"
      : expiry_status === "expired"
        ? "result.titleExpired"
        : "result.titleUnknown";

  const consensus =
    result.consensus_status != null
      ? t(`result.consensus.${result.consensus_status}`, {
          defaultValue: result.consensus_status,
        })
      : null;

  return (
    <section
      className="animate-slide-result space-y-6 rounded-2xl border border-teal-900/10 bg-white/70 p-6 shadow-[0_12px_40px_rgba(15,61,58,0.06)] backdrop-blur-sm sm:p-8"
      aria-live="polite"
      translate="no"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.14em] text-[var(--color-muted)]">
            {t("result.eyebrow")}
          </p>
          <h2 className="mt-1 text-2xl text-[var(--color-teal-950)] sm:text-3xl">
            {t(titleKey)}
          </h2>
        </div>
        <span
          className={`inline-flex items-center rounded-full px-3.5 py-1.5 text-sm font-semibold ${STATUS_CLASS[expiry_status]}`}
        >
          {t(`result.status.${expiry_status}`)}
        </span>
      </div>

      <dl className="grid gap-5 sm:grid-cols-2">
        <div>
          <dt className="text-sm text-[var(--color-muted)]">{t("result.mfg")}</dt>
          <dd className="mt-1 font-display text-2xl text-[var(--color-ink)]">
            {result.assessment.mfg_display || result.final_mfg || "—"}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-[var(--color-muted)]">{t("result.exp")}</dt>
          <dd className="mt-1 font-display text-2xl text-[var(--color-ink)]">
            {result.assessment.exp_display || result.final_exp || "—"}
          </dd>
        </div>
      </dl>

      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
            needs_human_review ? REVIEW_CLASS.needed : REVIEW_CLASS.clear
          }`}
        >
          {needs_human_review
            ? t("result.reviewNeeded")
            : t("result.reviewNotNeeded")}
        </span>
        {consensus && (
          <span className="text-sm text-[var(--color-muted)]">{consensus}</span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onListen}
          disabled={isSpeaking || isLoadingSpeech}
          className="cta-lift inline-flex items-center gap-2 rounded-lg bg-[var(--color-teal-800)] px-4 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60 disabled:shadow-none disabled:hover:transform-none"
          aria-pressed={isSpeaking}
        >
          <Volume2 className="size-4" aria-hidden />
          {isLoadingSpeech
            ? t("speech.loading")
            : isSpeaking
              ? t("result.speaking")
              : t("result.listen")}
        </button>

        {(isSpeaking || isLoadingSpeech) && (
          <button
            type="button"
            onClick={onStopSpeech}
            className="cta-lift inline-flex items-center gap-2 rounded-lg border border-teal-800/25 bg-white px-4 py-2.5 text-sm font-semibold text-[var(--color-teal-900)]"
            aria-label={t("result.stop")}
          >
            <Square className="size-3.5 fill-current" aria-hidden />
            {t("result.stop")}
          </button>
        )}
      </div>
    </section>
  );
}
