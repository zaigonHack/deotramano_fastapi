// frontend/src/components/PasswordStrength.jsx
import React, { useMemo } from "react";

const ALLOWED_SYMBOLS = "!@#$%^&*()_-+=[]{}:;,.?~";

// helpers
const hasLower  = (s) => /[a-z]/.test(s);
const hasUpper  = (s) => /[A-Z]/.test(s);
const hasDigit  = (s) => /\d/.test(s);
const hasSymbol = (s) =>
  new RegExp("[" + ALLOWED_SYMBOLS.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&") + "]").test(s);

// coincide con la política del backend
const policyOk = (p) => {
  if (!p) return false;
  if (p.length < 8 || p.length > 64) return false;
  if (!/^[A-Za-z0-9!@#$%^&*()_\-+=\[\]{}:;,.?~]+$/.test(p)) return false;
  return hasLower(p) && hasUpper(p) && hasDigit(p) && hasSymbol(p);
};

// scoring más robusto (0..4)
function score(p) {
  if (!p) return 0;
  const L = p.length;

  let s = 0;

  // Longitud
  if (L >= 8)  s += 1;
  if (L >= 12) s += 1;

  // Variedad
  let kinds = 0;
  if (hasLower(p))  kinds++;
  if (hasUpper(p))  kinds++;
  if (hasDigit(p))  kinds++;
  if (hasSymbol(p)) kinds++;
  if (kinds >= 2) s += 1;
  if (kinds >= 3) s += 1;

  // Penalizaciones por patrones triviales al inicio
  if (/^(?:1234|abcd|qwer|password|admin|1111|0000)/i.test(p)) {
    s = Math.max(0, s - 2);
  }

  // clamp a 0..4
  return s < 0 ? 0 : s > 4 ? 4 : s;
}

export default function PasswordStrength({ value = "" }) {
  const v = value ?? "";
  const sc = useMemo(() => score(v), [v]);
  const ok = useMemo(() => policyOk(v), [v]);

  const labels = ["Muy débil", "Débil", "Aceptable", "Buena", "Fuerte"];
  const colors = ["#d32f2f", "#ef6c00", "#f9a825", "#0077cc", "#2e7d32"];

  // estilos mínimos por si faltan en CSS global
  const barWrap = {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: 6,
    margin: "6px 0 2px",
  };
  const bar = (on) => ({
    height: 6,
    borderRadius: 999,
    background: on ? colors[sc] : "#e5e7eb",
    transition: "background .15s ease",
  });

  return (
    <div className="pw-meter-wrap" aria-live="polite">
      <div className="pw-meter" style={barWrap}>
        {[0, 1, 2, 3].map((i) => (
          <span key={i} style={bar(sc > i)} />
        ))}
      </div>

      <div className="pw-label" style={{ color: colors[sc], fontSize: ".92rem", marginBottom: 4 }}>
        {labels[sc]}
      </div>

      <ul className="pw-checklist" style={{ margin: "6px 0 4px", paddingLeft: "1.1rem", color: "#555" }}>
        <li className={v.length >= 8 ? "ok" : ""} style={{ listStyle: "disc" }}>
          Mínimo 8 caracteres
        </li>
        <li className={hasLower(v) ? "ok" : ""} style={{ listStyle: "disc" }}>
          Una minúscula
        </li>
        <li className={hasUpper(v) ? "ok" : ""} style={{ listStyle: "disc" }}>
          Una mayúscula
        </li>
        <li className={hasDigit(v) ? "ok" : ""} style={{ listStyle: "disc" }}>
          Un número
        </li>
        <li className={hasSymbol(v) ? "ok" : ""} style={{ listStyle: "disc" }}>
          Un símbolo permitido: <code>{ALLOWED_SYMBOLS}</code>
        </li>
      </ul>

      {ok && (
        <div className="pw-ok-hint" style={{ color: "#2e7d32", fontSize: ".9rem" }}>
          ✔ Cumple los requisitos.
        </div>
      )}
    </div>
  );
}
