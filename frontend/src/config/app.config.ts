/**
 * App Config
 * Global application configuration sourced from environment variables.
 */

export const AppConfig = {
  API_URL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000",
} as const;
