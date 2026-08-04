import { useCallback, useId, useRef, useState, type DragEvent } from "react";
import { useTranslation } from "react-i18next";
import { ImagePlus, X } from "lucide-react";

const ACCEPTED_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/bmp",
]);

const ACCEPT_ATTR =
  "image/jpeg,image/png,image/webp,image/bmp,.jpg,.jpeg,.png,.webp,.bmp";

function isAcceptedFile(file: File): boolean {
  if (ACCEPTED_TYPES.has(file.type)) return true;
  const name = file.name.toLowerCase();
  return (
    name.endsWith(".jpg") ||
    name.endsWith(".jpeg") ||
    name.endsWith(".png") ||
    name.endsWith(".webp") ||
    name.endsWith(".bmp")
  );
}

export interface ImageUploadZoneProps {
  file: File | null;
  previewUrl: string | null;
  disabled?: boolean;
  onFileSelect: (file: File) => void;
  onClear: () => void;
}

export default function ImageUploadZone({
  file,
  previewUrl,
  disabled = false,
  onFileSelect,
  onClear,
}: ImageUploadZoneProps) {
  const { t } = useTranslation();
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleFile = useCallback(
    (next: File | undefined | null) => {
      if (!next) return;
      if (!isAcceptedFile(next)) {
        setLocalError(t("upload.invalidType"));
        return;
      }
      setLocalError(null);
      onFileSelect(next);
    },
    [onFileSelect, t]
  );

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;
    handleFile(e.dataTransfer.files?.[0]);
  };

  return (
    <div className="space-y-3">
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        aria-labelledby={inputId}
        onKeyDown={(e) => {
          if (disabled) return;
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragEnter={(e) => {
          e.preventDefault();
          if (!disabled) setIsDragging(true);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setIsDragging(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          setIsDragging(false);
        }}
        onDrop={onDrop}
        onClick={() => {
          if (!disabled) inputRef.current?.click();
        }}
        className={[
          "relative flex min-h-[220px] cursor-pointer flex-col items-center justify-center overflow-hidden rounded-2xl border-2 border-dashed px-6 py-10 text-center transition",
          disabled ? "cursor-not-allowed opacity-60" : "",
          isDragging
            ? "border-[var(--color-teal-600)] bg-[var(--color-mint)]/60"
            : "border-teal-800/20 bg-white/55 hover:border-teal-700/40 hover:bg-white/75",
        ].join(" ")}
      >
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept={ACCEPT_ATTR}
          className="sr-only"
          disabled={disabled}
          onChange={(e) => {
            handleFile(e.target.files?.[0]);
            e.target.value = "";
          }}
        />

        {previewUrl ? (
          <>
            <img
              src={previewUrl}
              alt={t("upload.previewAlt")}
              className="max-h-56 w-full object-contain"
            />
            {file && (
              <p className="mt-3 max-w-full truncate text-sm text-[var(--color-muted)]">
                {file.name}
              </p>
            )}
          </>
        ) : (
          <>
            <span className="mb-3 flex size-12 items-center justify-center rounded-full bg-[var(--color-mint)] text-[var(--color-teal-800)]">
              <ImagePlus className="size-6" aria-hidden />
            </span>
            <p className="text-base font-medium text-[var(--color-ink)]">
              {t("upload.drop")}
            </p>
            <p className="mt-2 text-sm text-[var(--color-muted)]">
              {t("upload.formats")}
            </p>
          </>
        )}
      </div>

      {previewUrl && (
        <button
          type="button"
          onClick={onClear}
          disabled={disabled}
          className="inline-flex items-center gap-1.5 text-sm text-[var(--color-muted)] transition hover:text-[var(--color-teal-800)] disabled:opacity-50"
        >
          <X className="size-3.5" aria-hidden />
          {t("upload.clear")}
        </button>
      )}

      {localError && (
        <p className="text-sm text-[var(--color-danger)]" role="alert">
          {localError}
        </p>
      )}
    </div>
  );
}
