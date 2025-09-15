import React, { useMemo, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import "../styles/RegisterForm.css";
import { API_URL } from "../config";
import PasswordStrength from "../components/PasswordStrength"; // Barra de fuerza

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = useMemo(() => searchParams.get("token") || "", [searchParams]);
  const navigate = useNavigate();

  const [pwd1, setPwd1] = useState("");
  const [pwd2, setPwd2] = useState("");
  const [show, setShow] = useState(false);
  const [msg, setMsg] = useState("");
  const [ok, setOk] = useState(false);
  const [loading, setLoading] = useState(false);

  // Misma política que en backend
  const allowedSymbols = "!@#$%^&*()_-+=[]{}:;,.?~";
  const esc = (s) => s.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&");
  const policy = useMemo(() => {
    const cls = esc(allowedSymbols);
    return new RegExp(
      `^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[${cls}])[A-Za-z\\d${cls}]{8,64}$`
    );
  }, []);

  // Formatea mensajes del servidor (p.ej. password reutilizada)
  const prettyMsg = (raw) => {
    if (!raw) return "";
    const low = raw.toLowerCase();
    if (low.includes("ya has usado") || low.includes("ya la has utilizado")) {
      return "⚠️ Esa contraseña ya la has usado recientemente. Elige una distinta.";
    }
    return raw;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    setMsg("");
    setOk(false);

    if (!token) {
      setMsg("Falta el token de recuperación.");
      return;
    }
    if (pwd1 !== pwd2) {
      setMsg("Las contraseñas no coinciden.");
      return;
    }
    if (!policy.test(pwd1)) {
      setMsg(
        `Contraseña inválida. Debe tener 8–64 caracteres e incluir minúscula, mayúscula, número y un símbolo de: ${allowedSymbols}`
      );
      return;
    }

    try {
      setLoading(true);
      const resp = await fetch(`${API_URL}/api/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          new_password: pwd1,
          new_password_confirm: pwd2,
        }),
      });

      const text = await resp.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch {}

      if (!resp.ok) {
        throw new Error(data?.detail || "Error al actualizar la contraseña.");
      }

      setOk(true);
      setMsg("Contraseña actualizada con éxito. Ya puedes iniciar sesión.");
      // setTimeout(() => navigate("/login"), 1500);
    } catch (err) {
      setMsg(err.message || "Error del servidor.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-wrapper">
      <div className="form-container" style={{ maxWidth: 520 }}>
        <button
          type="button"
          className="back-btn"
          onClick={() => navigate(-1)}
          aria-label="Volver"
        >
          ← Volver
        </button>

        <h2 className="form-title">Establecer nueva contraseña</h2>

        <form onSubmit={handleSubmit} className="register-form" style={{ marginTop: 8 }}>
          <label className="form-label" htmlFor="rpw1">Nueva contraseña</label>
          <input
            id="rpw1"
            type={show ? "text" : "password"}
            className="form-input"
            placeholder="Nueva contraseña"
            value={pwd1}
            onChange={(e) => setPwd1(e.target.value)}
            required
            autoComplete="new-password"
          />

          {/* Barra de fuerza en vivo */}
          <PasswordStrength value={pwd1} />

          <label className="form-label" htmlFor="rpw2">Repite la nueva contraseña</label>
          <input
            id="rpw2"
            type={show ? "text" : "password"}
            className="form-input"
            placeholder="Repite la nueva contraseña"
            value={pwd2}
            onChange={(e) => setPwd2(e.target.value)}
            required
            autoComplete="new-password"
          />

          <div className="showpw-row">
            <input
              id="showpw"
              type="checkbox"
              className="checkbox-square"
              checked={show}
              onChange={(e) => setShow(e.target.checked)}
            />
            <label htmlFor="showpw">Mostrar contraseñas</label>
          </div>


          <button className="form-button" type="submit" disabled={loading}>
            {loading ? "Guardando…" : "Cambiar contraseña"}
          </button>

          <p style={{ fontSize: ".9em", color: "#455a64", marginTop: 10 }}>
            Requisitos: 8–64 caracteres, sin espacios, y debe incluir minúscula,
            mayúscula, número y un símbolo permitido:&nbsp;
            <code>!@#$%^&amp;*()_-+=[]&#123;&#125;:;,.?~</code>
          </p>

          {msg && (
            <p
              className={ok ? "success-message" : "error-message"}
              style={{
                marginTop: 10,
                fontWeight: ok ? "normal" : 600,
                color: ok ? "#2e7d32" : "#c62828",
              }}
              aria-live="polite"
              role="status"
            >
              {prettyMsg(msg)}
            </p>
          )}
        </form>
      </div>
    </div>
  );
}
