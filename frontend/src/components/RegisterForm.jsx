// src/components/RegisterForm.jsx
import React, { useState } from 'react';
import '../styles/RegisterForm.css'; // <-- ¡IMPORTANTE! Ajusta la ruta si hace falta
import { useNavigate } from 'react-router-dom';

const RegisterForm = () => {
  const [email, setEmail] = useState('');
  const [confirmEmail, setConfirmEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [name, setName] = useState('');
  const [surname, setSurname] = useState('');
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (email !== confirmEmail) {
      setMessage('Los correos no coinciden');
      setMessageType('error');
      return;
    }
    if (password !== confirmPassword) {
      setMessage('Las contraseñas no coinciden');
      setMessageType('error');
      return;
    }

    const data = {
      email,
      email_confirm: confirmEmail,
      password,
      password_confirm: confirmPassword,
      name,
      surname,
    };

    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      const result = await response.json();

      if (response.ok) {
        setMessage('Usuario registrado correctamente');
        setMessageType('success');
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      } else {
        setMessage(result.detail || 'Error al registrar el usuario');
        setMessageType('error');
      }
    } catch (error) {
      setMessage('Error al conectar con el servidor');
      setMessageType('error');
    }
  };

  return (
    <div className="form-wrapper">  {/* <-- OJO aquí */}
      <div className="form-container"> {/* <-- OJO aquí */}
        <h2 className="form-title">Registro</h2>
        <form onSubmit={handleSubmit} className="register-form">
          <label>Nombre</label>
          <input
            className="form-input"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

          <label>Apellido</label>
          <input
            className="form-input"
            type="text"
            value={surname}
            onChange={(e) => setSurname(e.target.value)}
            required
          />

          <label>Email</label>
          <input
            className="form-input"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <label>Confirmar Email</label>
          <input
            className="form-input"
            type="email"
            value={confirmEmail}
            onChange={(e) => setConfirmEmail(e.target.value)}
            required
          />

          <label>Contraseña</label>
          <input
            className="form-input"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <label>Repite la contraseña</label>
          <input
            className="form-input"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />

          <button className="form-button" type="submit">Registrarse</button>

          {message && (
            <p className={messageType === 'error' ? 'error-message' : 'success-message'}>
              {message}
            </p>
          )}
        </form>
      </div>
    </div>
  );
};

export default RegisterForm;

