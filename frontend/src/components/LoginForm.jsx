// src/components/LoginForm.jsx
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import "../styles/RegisterForm.css";
import { API_URL } from "../config";

// BASE del backend
// - En dev: VITE_API_URL (p.ej. http://127.0.0.1:8000)
// - En prod: "" -> mismo origen (rutas relativas)
const BASE = (API_URL || "").replace(/\/+$/, ""); // "" -> mismo origen en prod
const endpoint = `${BASE}/api/auth/login`;

export default function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      const savedUser = JSON.parse(localStorage.getItem("user") || "{}");
      if (savedUser?.is_admin) navigate("/admin");
      else navigate("/dashboard");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  async function readBody(resp) {
    const text = await resp.text();
    try {
      return text ? JSON.parse(text) : {};
    } catch {
      return { raw: text };
    }
  }

  function toQS(obj) {
    const p = new URLSearchParams();
    Object.entries(obj).forEach(([k, v]) => p.append(k, v));
    return p.toString();
  }

  async function tryLogin() {
    // 1) JSON { email, password }
    let resp = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });
    let data = await readBody(resp);
    if (resp.ok) return data;

    // 2) JSON { username, password }
    if ([400, 401, 415, 422].includes(resp.status)) {
      resp = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username: email, password }),
      });
      data = await readBody(resp);
      if (resp.ok) return data;
    }

    // 3) x-www-form-urlencoded username/password
    if ([400, 401, 415, 422].includes(resp.status)) {
      resp = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        credentials: "include",
        body: toQS({ username: email, password }),
      });
      data = await readBody(resp);
      if (resp.ok) return data;
    }

    // Si sigue mal, lanzamos detalle
    const msg =
      data?.detail ||
      data?.message ||
      data?.error ||
      (typeof data?.raw === "string" && data.raw) ||
      `Error ${resp.status}`;
    const err = new Error(msg);
    err.status = resp.status;
    throw err;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await tryLogin();
      const token = data?.access_token || data?.token;
      if (!token) throw new Error("No se recibió token de autenticación");

      const user = data?.user || {};
      if (typeof login === "function") {
        login(token, user);
      } else {
        localStorage.setItem("token", token);
        localStorage.setItem("user", JSON.stringify(user));
      }

      if (user?.is_admin) navigate("/admin");
      else navigate("/dashboard");
    } catch (err) {
      console.error("Login error:", err);
      setError(err.message || "No se pudo iniciar sesión");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-container">
      <form onSubmit={handleSubmit} className="auth-form" autoComplete="on">
        <h2 className="form-title">Iniciar sesión</h2>
        {error && <p className="error-message">{error}</p>}

        <label htmlFor="email">Email</label>
        <input
          className="form-input"
          id="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <label htmlFor="password">Contraseña</label>
        <input
          className="form-input"
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <button
          type="submit"
          className="form-button"
          style={{ marginBottom: "0.7rem" }}
          disabled={loading}
        >
          {loading ? "Entrando..." : "Entrar"}
        </button>

        <button
          type="button"
          className="form-button"
          style={{ marginBottom: 0 }}
          onClick={() => navigate("/forgot-password")}
        >
          ¿Has olvidado tu contraseña?
        </button>
      </form>
    </div>
  );
}
