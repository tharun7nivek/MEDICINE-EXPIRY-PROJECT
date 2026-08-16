import { useCallback, useEffect, useRef, useState } from "react";
import type { ExpiryStatus } from "../types/detect.types";
import { detectService } from "../services/detectService";

export type SpeechErrorCode = "error";

export interface SpeakResult {
  ok: boolean;
  error?: SpeechErrorCode;
  cancelled?: boolean;
}

function revokeUrl(url: string | null) {
  if (url) URL.revokeObjectURL(url);
}

/**
 * Plays a server-synthesized expiry summary (Edge neural TTS).
 */
export function useSpeech() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isLoadingSpeech, setIsLoadingSpeech] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const stopPlayback = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
      audioRef.current = null;
    }
    revokeUrl(objectUrlRef.current);
    objectUrlRef.current = null;
    setIsSpeaking(false);
    setIsLoadingSpeech(false);
  }, []);

  useEffect(() => {
    return () => {
      stopPlayback();
    };
  }, [stopPlayback]);

  const speakExpirySummary = useCallback(
    async (
      lang: string,
      mfg: string | null,
      exp: string | null,
      status: ExpiryStatus,
      needsReview = false
    ): Promise<SpeakResult> => {
      stopPlayback();

      const controller = new AbortController();
      abortRef.current = controller;
      setIsLoadingSpeech(true);

      try {
        const blob = await detectService.speakExpirySummary(
          {
            lang: lang.split("-")[0] ?? "en",
            expiry_status: status,
            mfg_display: mfg,
            exp_display: exp,
            needs_human_review: needsReview,
          },
          controller.signal
        );

        if (controller.signal.aborted) {
          return { ok: false, cancelled: true };
        }

        const objectUrl = URL.createObjectURL(blob);
        objectUrlRef.current = objectUrl;
        const audio = new Audio(objectUrl);
        audioRef.current = audio;

        audio.onended = () => {
          setIsSpeaking(false);
          revokeUrl(objectUrlRef.current);
          objectUrlRef.current = null;
          audioRef.current = null;
        };
        audio.onerror = () => {
          setIsSpeaking(false);
          setIsLoadingSpeech(false);
          revokeUrl(objectUrlRef.current);
          objectUrlRef.current = null;
          audioRef.current = null;
        };

        setIsLoadingSpeech(false);
        setIsSpeaking(true);
        await audio.play();
        return { ok: true };
      } catch {
        if (controller.signal.aborted) {
          return { ok: false, cancelled: true };
        }
        setIsLoadingSpeech(false);
        setIsSpeaking(false);
        return { ok: false, error: "error" };
      }
    },
    [stopPlayback]
  );

  return {
    speakExpirySummary,
    cancel: stopPlayback,
    isSpeaking,
    isLoadingSpeech,
  };
}
