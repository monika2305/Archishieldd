let rawUrl = (import.meta.env.VITE_API_URL || "http://localhost:8001").trim();
if (rawUrl.endsWith("/")) {
  rawUrl = rawUrl.slice(0, -1);
}
export const API_BASE_URL = rawUrl;
