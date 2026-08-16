import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import SiteHeader from "../../../components/layout/SiteHeader";
import { useDetect } from "../hooks/useDetect";
import { useSpeech } from "../hooks/useSpeech";
import DetectionResultCard from "./DetectionResultCard";
import ImageUploadZone from "./ImageUploadZone";

export default function DetectionPage() {
  const { t, i18n } = useTranslation();
  const { isLoading, error, result, detect, refreshDisplayLang, reset } = useDetect();
  const {
    speakExpirySummary,
    cancel: cancelSpeech,
    isSpeaking,
    isLoadingSpeech,
  } = useSpeech();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  useEffect(() => {
    if (!result) return;
    void refreshDisplayLang(i18n.language);
  }, [i18n.language]);

  const clearSelection = useCallback(() => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setPreviewUrl(null);
    reset();
    cancelSpeech();
  }, [previewUrl, reset, cancelSpeech]);

  const onFileSelect = useCallback(
    (next: File) => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setFile(next);
      setPreviewUrl(URL.createObjectURL(next));
      reset();
      cancelSpeech();
    },
    [previewUrl, reset, cancelSpeech]
  );

  const onSubmit = async () => {
    if (!file) {
      toast.error(t("detect.selectFirst"));
      return;
    }
    cancelSpeech();
    const response = await detect(file, i18n.language);
    if (!response) {
      toast.error(t("detect.detectFailed"));
    }
  };

  const onListen = async () => {
    if (!result) return;

    const outcome = await speakExpirySummary(
      i18n.language,
      result.assessment.mfg_display || result.final_mfg,
      result.assessment.exp_display || result.final_exp,
      result.assessment.expiry_status,
      result.assessment.needs_human_review
    );

    if (!outcome.ok && !outcome.cancelled) {
      toast.error(t("speech.error"));
    }
  };

  return (
    <div className="min-h-screen">
      <SiteHeader />

      <main className="mx-auto max-w-3xl px-5 py-10 sm:px-8 sm:py-14">
        <div className="animate-fade-up">
          <p className="text-sm font-medium uppercase tracking-[0.14em] text-[var(--color-teal-700)]">
            {t("detect.eyebrow")}
          </p>
          <h1 className="mt-2 text-3xl text-[var(--color-teal-950)] sm:text-4xl">
            {t("detect.title")}
          </h1>
          <p className="mt-3 max-w-xl text-base leading-relaxed text-[var(--color-muted)]">
            {t("detect.subtitle")}
          </p>
        </div>

        <div className="mt-10 space-y-6">
          <ImageUploadZone
            file={file}
            previewUrl={previewUrl}
            disabled={isLoading}
            onFileSelect={onFileSelect}
            onClear={clearSelection}
          />

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={onSubmit}
              disabled={!file || isLoading}
              className="cta-lift inline-flex items-center justify-center gap-2 rounded-lg bg-[var(--color-teal-800)] px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none disabled:hover:transform-none"
            >
              {isLoading ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                  {t("detect.analyzing")}
                </>
              ) : (
                t("detect.analyze")
              )}
            </button>
          </div>

          {isLoading && (
            <div
              className="animate-fade-in flex items-start gap-3 rounded-xl border border-teal-800/15 bg-[var(--color-mint)]/50 px-4 py-4"
              role="status"
              aria-live="polite"
            >
              <Loader2
                className="mt-0.5 size-5 shrink-0 animate-spin text-[var(--color-teal-700)]"
                aria-hidden
              />
              <div>
                <p className="text-sm font-semibold text-[var(--color-teal-950)]">
                  {t("detect.loadingTitle")}
                </p>
                <p className="mt-1 text-sm leading-relaxed text-[var(--color-muted)]">
                  {t("detect.loadingHint")}
                </p>
              </div>
            </div>
          )}

          {error && !isLoading && (
            <p
              className="animate-fade-in rounded-lg bg-[var(--color-danger-soft)] px-4 py-3 text-sm text-[var(--color-danger)]"
              role="alert"
            >
              {error}
            </p>
          )}

          {result && !isLoading && (
            <DetectionResultCard
              result={result}
              onListen={onListen}
              onStopSpeech={cancelSpeech}
              isSpeaking={isSpeaking}
              isLoadingSpeech={isLoadingSpeech}
            />
          )}
        </div>
      </main>
    </div>
  );
}
