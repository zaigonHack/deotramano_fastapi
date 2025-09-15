// Usa VITE_API_URL si existe; si viene vacío ("") en prod → usa rutas relativas
const BASE = (import.meta.env.VITE_API_URL || "").trim();

export const apiUrl = (path) => `${BASE}${path}`;

export async function apiFetch(path, options = {}) {
  const res = await fetch(apiUrl(path), options);
  return res;
}
