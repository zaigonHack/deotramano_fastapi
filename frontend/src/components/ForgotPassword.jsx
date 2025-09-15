import React, { useState } from 'react';
import '../styles/RegisterForm.css';
import { API_URL } from '../config';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState(null); // { success: boolean, message: string }
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus(null);
    setLoading(true);

    try {
      const resp = await fetch(`${API_URL}/api/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      // La API devuelve { message: "..." }
      const text = await resp.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch {}

      if (resp.ok) {
        setStatus({
          success: true,
          // Si el backend trae un mensaje concreto, úsalo; si no, muestra uno amistoso
          message: data.message || 'Si el correo existe, te hemos enviado un email con instrucciones para recuperar tu cuenta.',
        });
      } else {
        setStatus({
          success: false,
          message: data.detail || 'No se pudo procesar la solicitud.',
        });
      }
    } catch {
      setStatus({ success: false, message: 'Error de conexión con el servidor.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-wrapper">
      <form className="form-container" onSubmit={handleSubmit}>
        <h2 className="form-title">Recupera tu contraseña</h2>

        <label htmlFor="email" className="form-label">Correo electrónico</label>
        <input
          type="email"
          id="email"
          className="form-input"
          placeholder="ejemplo@correo.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />

        <button type="submit" className="form-button" disabled={loading}>
          {loading ? 'Enviando…' : 'Enviar enlace'}
        </button>

        {status && (
          <p
            className={status.success ? 'success-message' : 'error-message'}
            style={{ marginTop: '1rem', textAlign: 'center' }}
            aria-live="polite"
          >
            {status.message}
          </p>
        )}
      </form>
    </div>
  );
};

export default ForgotPassword;





