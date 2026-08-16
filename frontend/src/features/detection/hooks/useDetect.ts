import { useCallback, useState } from "react";
import { detectService } from "../services/detectService";
import type { DetectResponse } from "../types/detect.types";

type FastApiDetailItem = { msg?: string; message?: string };

function extractFastApiDetail(err: unknown): string {
  const e = err as {
    code?: string;
    message?: string;
    response?: {
      status?: number;
      data?: string | { detail?: unknown };
    };
  };

  if (e?.code === "ECONNABORTED") {
    return "Detection timed out. The vision pipeline can take several minutes — please try again.";
  }

  if (!e?.response) {
    return e?.message?.includes("Network")
      ? "Cannot reach the detection API. Confirm the backend is running on port 8000."
      : (e?.message ?? "Detection request failed.");
  }

  const data = e.response.data;
  if (typeof data === "string" && data.trim()) return data;

  const detail = data && typeof data === "object" ? data.detail : undefined;

  if (typeof detail === "string" && detail.trim()) return detail;

  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (!item || typeof item !== "object") return null;
        const entry = item as FastApiDetailItem;
        return entry.msg ?? entry.message ?? null;
      })
      .filter((part): part is string => Boolean(part && part.trim()));
    if (parts.length > 0) return parts.join("; ");
  }

  if (detail && typeof detail === "object") {
    const entry = detail as FastApiDetailItem;
    const message = entry.msg ?? entry.message;
    if (typeof message === "string" && message.trim()) return message;
  }

  if (e.response.status === 415) {
    return "Unsupported image type. Please use JPEG, PNG, WebP, or BMP.";
  }

  return e?.message ?? "Detection request failed.";
}

export interface UseDetectReturn {
  isLoading: boolean;
  error: string | null;
  result: DetectResponse | null;
  detect: (file: File, lang?: string) => Promise<DetectResponse | null>;
  refreshDisplayLang: (lang: string) => Promise<void>;
  reset: () => void;
}

export function useDetect(): UseDetectReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DetectResponse | null>(null);

  const reset = useCallback(() => {
    setIsLoading(false);
    setError(null);
    setResult(null);
  }, []);

  const detect = useCallback(async (file: File, lang = "en"): Promise<DetectResponse | null> => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await detectService.detect(file, lang);
      setResult(response);
      return response;
    } catch (err) {
      const message = extractFastApiDetail(err);
      setError(message);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshDisplayLang = useCallback(async (lang: string) => {
    if (!result) return;
    const res = await detectService.assess({
      final_mfg: result.final_mfg,
      final_exp: result.final_exp,
      status: result.status,
      lang,
    });
    setResult({ ...result, assessment: res.assessment });
  }, [result]);

  return { isLoading, error, result, detect, refreshDisplayLang, reset };
}
