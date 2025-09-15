// src/config.js
const RAW = (import.meta.env.VITE_API_URL || "").trim();

// En dev: RAW vendrá con "http://127.0.0.1:8000"
// En prod: RAW será "" -> usamos mismo origen (rutas relativas)
export const API_URL = RAW
  ? RAW.replace(/\/$/, "")
  : ""; // prod => "" => fetch('/api/...') al mismo host del frontend
