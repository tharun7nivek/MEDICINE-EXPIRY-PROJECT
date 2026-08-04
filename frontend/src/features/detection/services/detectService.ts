import axiosClient from "../../../lib/axiosClient";
import type {
  AssessRequest,
  AssessResponse,
  DetectResponse,
  HealthResponse,
} from "../types/detect.types";

export const detectService = {
  /**
   * POST /api/v1/detect
   * Multipart upload of a medicine pack image; returns MFG/EXP + assessment.
   */
  async detect(file: File): Promise<DetectResponse> {
    const formData = new FormData();
    formData.append("file", file);

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
};
