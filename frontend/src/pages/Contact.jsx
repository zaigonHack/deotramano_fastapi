// src/pages/Contact.jsx
import React, { useState, useMemo } from "react";
import { useAuth } from "../context/AuthContext";
import { API_URL } from "../config";

const MAX_CHARS = 500;
// "" en prod => mismo origen; en dev VITE_API_URL
const BASE = (API_URL || "").replace(/\/$/, "") || "";

export default function Contact() {
  const { isAuthenticated, user } = useAuth();
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [ok, setOk] = useState("");
  const [err, setErr] = useState("");

  const remaining = useMemo(() => MAX_CHARS - message.length, [message]);
  const isValid =
    subject.trim().length >= 3 &&
    message.trim().length >= 10 &&
    message.length <= MAX_CHARS;

  const onSubmit = async (e) => {
    e.preventDefault();
    setOk("");
    setErr("");

    if (!isAuthenticated) {
      setErr("Debes iniciar sesión para enviar el formulario.");
      return;
    }
    if (!isValid) {
      setErr("Asunto mínimo 3 caracteres y mensaje mínimo 10.");
      return;
    }

    try {
      setSending(true);
      const token = localStorage.getItem("token") || "";

      const fd = new FormData();
      fd.append("subject", subject.trim());
      fd.append("message", message.trim());
      if (user?.email) fd.append("email", user.email);

      const resp = await fetch(`${BASE}/api/contact`, {
        method: "POST",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: "include",
        body: fd,
      });

      if (!resp.ok) {
        const text = await resp.text();
        let msg = `Error ${resp.status}`;
        try {
          const data = text ? JSON.parse(text) : {};
          if (typeof data?.detail === "string") msg = data.detail;
          else if (Array.isArray(data?.detail) && data.detail[0]?.msg)
            msg = data.detail[0].msg;
        } catch {}
        throw new Error(msg);
      }

      setOk("Mensaje enviado. ¡Gracias por contactarnos!");
      setSubject("");
      setMessage("");
    } catch (e) {
      setErr(e.message || "No se pudo enviar el mensaje.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="form-container">
      <h2 className="form-title">Contacto</h2>

      <form
        className="form"
        onSubmit={onSubmit}
        style={{
          background: "#ffffff",
          color: "#111",
          borderRadius: 12,
          boxShadow: "0 2px 14px rgba(0,0,0,0.06)",
          padding: 18,
        }}
      >
        {!isAuthenticated && (
          <div className="error-message" style={{ marginBottom: "1rem" }}>
            Debes iniciar sesión para usar el formulario de contacto.
          </div>
        )}

        <label className="form-label" style={{ color: "#111" }}>
          Asunto
        </label>
        <input
          type="text"
          className="form-input"
          placeholder="Escribe el asunto"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          maxLength={120}
          disabled={sending || !isAuthenticated}
          style={{ background: "#fff", color: "#111", borderColor: "#c7daf0" }}
        />

        <label className="form-label" style={{ color: "#111", marginTop: 10 }}>
          Mensaje
        </label>
        <textarea
          className="form-textarea"
          placeholder="Cuéntanos tu consulta..."
          value={message}
          onChange={(e) =>
            e.target.value.length <= MAX_CHARS && setMessage(e.target.value)
          }
          rows={8}
          maxLength={MAX_CHARS}
          disabled={sending || !isAuthenticated}
          style={{
            background: "#fff",
            color: "#111",
            borderColor: "#c7daf0",
            minHeight: 160,
            width: "100%", // mismo ancho que Asunto
          }}
        />

        <div
          style={{
            textAlign: "right",
            fontSize: "0.9em",
            marginTop: 6,
            color: remaining < 50 ? "#c0392b" : "#666",
          }}
          aria-live="polite"
        >
          {remaining} caracteres restantes
        </div>

        <button
          type="submit"
          className="form-button"
          disabled={sending || !isAuthenticated || !isValid}
          style={{ marginTop: 12 }}
          title={!isValid ? "Asunto ≥ 3 y mensaje ≥ 10" : ""}
        >
          {sending ? "Enviando..." : "Enviar"}
        </button>

        {ok && (
          <div className="success-message" style={{ marginTop: 10 }}>
            {ok}
          </div>
        )}
        {err && (
          <div className="error-message" style={{ marginTop: 10 }}>
            {err}
          </div>
        )}
      </form>
    </div>
  );
}
