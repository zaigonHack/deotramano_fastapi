import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { API_URL } from "../config";
import { useAuth } from "../context/AuthContext";
import PasswordStrength from "../components/PasswordStrength";

export default function ChangePassword() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const token = useMemo(() => localStorage.getItem("token") || "", []);
  const authHeaders = useMemo(
    () => (token ? { Authorization: `Bearer ${token}` } : {}),
    [token]
  );

  const [oldPwd, setOldPwd] = useState("");
  const [pwd1, setPwd1] = useState("");
  const [pwd2, setPwd2] = useState("");
  const [show, setShow] = useState(false);
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");

  // Símbolos permitidos (coinciden con el backend)
  const allowedSymbols = "!@#$%^&*()_-+=[]{}:;,.?~";

  // Escapar para usar en RegExp
  const esc = (s) => s.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&");

  // Política: 8–64, 1 minúscula, 1 mayúscula, 1 dígito, 1 símbolo permitido
  const policyRegex = useMemo(() => {
    const cls = esc(allowedSymbols);
    return new RegExp(
      `^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[${cls}])[A-Za-z\\d${cls}]{8,64}$`
    );
  }, []);

  const validateClient = () => {
    if (!oldPwd || !pwd1 || !pwd2) return "Rellena todos los campos.";
    if (pwd1 !== pwd2) return "La nueva contraseña y su confirmación no coinciden.";
    if (!policyRegex.test(pwd1)) {
      return (
        "Contraseña inválida. Debe tener entre 8 y 64 caracteres, " +
        "incluir al menos una minúscula, una mayúscula, un número y un símbolo de: " +
        allowedSymbols
      );
    }
    return "";
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErr("");
    setOk("");

    if (!isAuthenticated) {
      setErr("Debes iniciar sesión.");
      return;
    }

    const v = validateClient();
    if (v) {
      setErr(v);
      return;
    }

    try {
      const resp = await fetch(`${API_URL}/api/auth/change-password`, {
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...authHeaders,
        },
        body: JSON.stringify({
          current_password: oldPwd,
          new_password: pwd1,
          new_password_confirm: pwd2,
        }),
      });

      const text = await resp.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch {}

      if (!resp.ok) {
        const msg =
          data?.detail ||
          data?.message ||
          (resp.status === 401
            ? "Sesión inválida. Vuelve a iniciar sesión."
            : `Error ${resp.status}`);
        throw new Error(msg);
      }

      setOk("Contraseña cambiada correctamente.");
      setOldPwd("");
      setPwd1("");
      setPwd2("");
    } catch (e) {
      setErr(e.message || "No se pudo cambiar la contraseña.");
    }
  };

  return (
    <div className="form-container" style={{ maxWidth: 520 }}>
      {/* Botón Volver */}
      <button
        type="button"
        className="form-button"
        onClick={() => navigate(-1)}
        style={{ marginBottom: 24, marginTop: 16 }}
      >
        Volver
      </button>

      <h2 className="form-title">Cambiar contraseña</h2>

      <form onSubmit={handleSubmit} className="form-group" style={{ gap: 12 }}>
        <label className="form-label" htmlFor="current-password">
          Contraseña actual
        </label>
        <input
          id="current-password"
          type={show ? "text" : "password"}
          className="form-input"
          value={oldPwd}
          onChange={(e) => setOldPwd(e.target.value)}
          autoComplete="current-password"
        />

        <label className="form-label" htmlFor="new-password">
          Nueva contraseña
        </label>
        <input
          id="new-password"
          type={show ? "text" : "password"}
          className="form-input"
          value={pwd1}
          onChange={(e) => setPwd1(e.target.value)}
          autoComplete="new-password"
        />

        {/* Barra de fuerza (¡importante: prop 'value'!) */}
        <PasswordStrength value={pwd1} />

        <label className="form-label" htmlFor="new-password-2">
          Repite la nueva contraseña
        </label>
        <input
          id="new-password-2"
          type={show ? "text" : "password"}
          className="form-input"
          value={pwd2}
          onChange={(e) => setPwd2(e.target.value)}
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


        {err && (
          <div className="error-message" style={{ marginTop: 8 }}>
            {err}
          </div>
        )}

        {ok && (
          <div
            className="success-message"
            style={{
              marginTop: 8,
              background: "#e8f5e9",
              color: "#2e7d32",
              padding: "8px 12px",
              borderRadius: 8,
            }}
          >
            {ok}
          </div>
        )}

        <button className="form-button" type="submit" style={{ marginTop: 8 }}>
          Guardar contraseña
        </button>

        <p style={{ fontSize: ".9em", color: "#455a64", marginTop: 8 }}>
          Requisitos: 8–64 caracteres, sin espacios, con al menos una letra
          minúscula, una mayúscula, un número y un símbolo permitido:&nbsp;
          <code>!@#$%^&amp;*()_-+=[]&#123;&#125;:;,.?~</code>
        </p>
      </form>
    </div>
  );
}
