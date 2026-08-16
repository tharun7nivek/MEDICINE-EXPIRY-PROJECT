/**
 * Types mirroring AGENTIC_MEDICINE_PROJECT/src/api/schemas/detect_api.py
 * and expiry_assessment.py
 */

export type DetectStatus = "accepted" | "human_review";

export type ConsensusStatus = "match" | "mismatch" | "low_confidence";

export type CropSource = "yolo" | "full_image_fallback";

export type HealthStatus = "ok" | "degraded";

/** Backend-computed expiry verdict (no client-side date math). */
export type ExpiryStatus = "valid" | "expired" | "unknown";

export type DatePrecision = "day" | "month";

/** Boolean checks from the deterministic validate node. */
export interface DetectValidation {
  mfg_parsed?: boolean;
  exp_parsed?: boolean;
  exp_after_mfg?: boolean;
  exp_in_future?: boolean;
  reflection_unresolved?: boolean;
  [key: string]: unknown;
}

/** Deterministic assessment computed by the backend. */
export interface ExpiryAssessment {
  expiry_status: ExpiryStatus;
  is_expired: boolean | null;
  needs_human_review: boolean;
  mfg_parsed: boolean;
  exp_parsed: boolean;
  mfg_iso: string | null;
  exp_iso: string | null;
  exp_valid_through: string | null;
  exp_precision: DatePrecision | null;
  mfg_display: string | null;
  exp_display: string | null;
  display_lang: string;
}

export interface ModelsUsed {
  first: string | null;
  second: string | null;
  reflection: string | null;
}

export interface DetectResponse {
  status: DetectStatus;
  final_mfg: string | null;
  final_exp: string | null;
  consensus_status: ConsensusStatus | null;
  validation: DetectValidation;
  assessment: ExpiryAssessment;
  bbox_2d: number[] | null;
  crop_source: CropSource | null;
  crop_path: string;
  models_used: ModelsUsed;
  first_result: Record<string, unknown>;
  second_result: Record<string, unknown>;
  reflection_result: Record<string, unknown> | null;
  request_id: string;
  elapsed_ms: number;
  model_pipeline: string;
}

export interface HealthResponse {
  status: HealthStatus;
  version: string;
  yolo_loaded: boolean;
  openrouter_keys: number;
  groq_keys: number;
  storage_dir: string;
  tts_configured?: boolean;
}

export interface SpeechExpirySummaryRequest {
  lang: string;
  expiry_status: ExpiryStatus;
  mfg_display: string | null;
  exp_display: string | null;
  needs_human_review: boolean;
}

export interface AssessRequest {
  final_mfg?: string | null;
  final_exp?: string | null;
  status?: DetectStatus;
  lang?: string;
}

export interface AssessResponse {
  final_mfg: string | null;
  final_exp: string | null;
  status: DetectStatus;
  assessment: ExpiryAssessment;
}
