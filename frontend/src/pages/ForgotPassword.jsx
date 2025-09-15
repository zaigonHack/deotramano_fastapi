// src/pages/ForgotPassword.jsx
import React, { useState } from "react";
import { API_URL } from "../config";
import "../styles/RegisterForm.css";

// "" en prod ⇒ mismo origen
const BASE = (API_URL || "").replace(/\/$/, "");

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage("");
    setSending(true);
    try {
      const resp = await fetch(`${BASE}/api/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email }),
      });

      const text = await resp.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch {}

      if (resp.ok) {
        setMessage("Revisa tu correo para el enlace de recuperación.");
      } else {
        setMessage(data?.detail || `Error ${resp.status}`);
      }
    } catch {
      setMessage("Error del servidor.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="form-container">
      <form className="auth-form" onSubmit={handleSubmit}>
        <h2 className="form-title">Recuperar contraseña</h2>

        <label htmlFor="email">Email</label>
        <input
          id="email"
          className="form-input"
          type="email"
          placeholder="Introduce tu email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <button className="form-button" type="submit" disabled={sending}>
          {sending ? "Enviando…" : "Enviar enlace"}
        </button>

        {message && <p style={{ marginTop: "0.75rem" }}>{message}</p>}
      </form>
    </div>
  );
}
