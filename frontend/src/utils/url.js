// frontend/src/url.js

export const API =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

// Construye URL de imágenes
export function imageUrl(pathOrUrl) {
  if (!pathOrUrl) return "";
  if (/^https?:\/\//i.test(pathOrUrl)) return pathOrUrl;
  const path = pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`;
  return `${API}${path}`;
}

// =======================
// Helpers para llamadas API
// =======================

// Obtener token desde localStorage
function getToken() {
  try {
    return localStorage.getItem("token") || "";
  } catch {
    return "";
  }
}

// Headers con autenticación
export function authHeaders(json = true) {
  const h = {};
  const t = getToken();
  if (t) h["Authorization"] = `Bearer ${t}`;
  if (json) h["Content-Type"] = "application/json";
  return h;
}

// POST genérico
export async function apiPost(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${txt || res.statusText}`);
  }
  return res.json().catch(() => ({}));
}
