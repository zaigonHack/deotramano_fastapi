// src/Dashboard.jsx
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from "./context/AuthContext.jsx";

const Dashboard = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    } else if (user?.is_admin) {
      navigate('/admin');
    }
  }, [isAuthenticated, user, navigate]);

  const handleCreateAd = () => navigate('/create-ad');
  const handleViewAds = () => navigate('/my-ads');
  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="form-container">
      <h2>Bienvenido, {user?.name ? user.name : "usuario"}!</h2>
      <p>¿Qué quieres hacer hoy?</p>
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          margin: '2rem 0',
          alignItems: 'center'
        }}
      >
        <button
          className="form-button dashboard-btn"
          onClick={() => navigate("/change-password")}
        >
          Cambiar contraseña
        </button>

        <button className="form-button dashboard-btn" onClick={handleCreateAd}>
          Crear anuncio
        </button>

        <button className="form-button dashboard-btn" onClick={handleViewAds}>
          Ver mis anuncios
        </button>

        <button
          className="form-button dashboard-btn"
          style={{ backgroundColor: '#e53935', color: 'white' }}
          onClick={handleLogout}
        >
          Cerrar sesión
        </button>
      </div>
    </div>
  );
};

export default Dashboard;
