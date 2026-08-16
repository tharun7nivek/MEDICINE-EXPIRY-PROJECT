import axiosClient from "../../../lib/axiosClient";
import type {
  AssessRequest,
  AssessResponse,
  DetectResponse,
  HealthResponse,
  SpeechExpirySummaryRequest,
} from "../types/detect.types";

export const detectService = {
  /**
   * POST /api/v1/detect
   * Multipart upload of a medicine pack image; returns MFG/EXP + assessment.
   */
  async detect(file: File, lang = "en"): Promise<DetectResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("lang", lang.split("-")[0] ?? "en");

    const response = await axiosClient.post<DetectResponse>(
      "/api/v1/detect",
      formData
    );
    return response.data;
  },

  /**
   * POST /api/v1/assess
   * Deterministic expiry assessment from MFG/EXP strings (backend-only math).
   */
  async assess(body: AssessRequest): Promise<AssessResponse> {
    const response = await axiosClient.post<AssessResponse>(
      "/api/v1/assess",
      body
    );
    return response.data;
  },

  /**
   * GET /api/v1/health
   * Readiness probe (keys + YOLO load state).
   */
  async health(): Promise<HealthResponse> {
    const response = await axiosClient.get<HealthResponse>("/api/v1/health");
    return response.data;
  },

  /**
   * POST /api/v1/speech/expiry-summary
   * Returns an MP3 blob of the spoken assessment in ``lang``.
   */
  async speakExpirySummary(
    body: SpeechExpirySummaryRequest,
    signal?: AbortSignal
  ): Promise<Blob> {
    const response = await axiosClient.post<Blob>(
      "/api/v1/speech/expiry-summary",
      body,
      {
        responseType: "blob",
        timeout: 30000,
        signal,
      }
    );
    const data = response.data;
    if (!(data instanceof Blob) || data.size === 0) {
      throw new Error("Empty speech audio");
    }
    const contentType = String(response.headers["content-type"] ?? "");
    if (contentType.includes("application/json")) {
      throw new Error("Speech endpoint returned JSON");
    }
    return data;
  },
};
