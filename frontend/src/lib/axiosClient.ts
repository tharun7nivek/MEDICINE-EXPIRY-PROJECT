/**
 * Axios instance for the Medicine Expiry detection API.
 * - baseURL from AppConfig.API_URL
 * - long timeout for VLM pipeline
 * - no auth interceptors
 * - FormData leaves Content-Type unset so the browser sets multipart boundary
 */

import axios from "axios";
import { AppConfig } from "../config/app.config";

const axiosClient = axios.create({
  baseURL: AppConfig.API_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 300000,
});

axiosClient.interceptors.request.use(
  (config) => {
    if (config.data instanceof FormData) {
      config.headers.setContentType(false);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default axiosClient;
