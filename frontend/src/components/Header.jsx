// src/components/Header.jsx
import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./Header.css";
import logo from "../assets/logo.png";
import { useAuth } from "../context/AuthContext";

const Header = () => {
  const [menuOpen, setMenuOpen] = useState(false);
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleBackdropClick = () => setMenuOpen(false);

  const handleLogout = () => {
    setMenuOpen(false);
    logout();
    navigate("/login");
  };

  return (
    <header className="header">
      <div className="logo-title">
        <Link to="/" className="logo-link" aria-label="Inicio">
          <img src={logo} alt="Logo DeOtraMano" className="logo-img" />
        </Link>
        <span className="logo-text">DeOtraMano</span>
      </div>

      {/* Navegación de escritorio */}
      <nav className="nav-links desktop" aria-label="Principal">
        {!isAuthenticated ? (
          <>
            <Link to="/register" className="nav-btn">Registro</Link>
            <Link to="/login" className="nav-btn">Iniciar sesión</Link>
          </>
        ) : (
          <>
            <Link to="/create-ad" className="nav-btn">Crear anuncio</Link>
            <Link to="/my-ads" className="nav-btn">Mis anuncios</Link>
            <Link to="/contact" className="nav-btn">Contacto</Link>
            <button className="nav-btn logout-btn" onClick={handleLogout}>
              Cerrar sesión
            </button>
          </>
        )}
      </nav>

      {/* Botón hamburguesa (móvil) */}
      <button
        className="menu-toggle"
        aria-label={menuOpen ? "Cerrar menú" : "Abrir menú"}
        aria-expanded={menuOpen}
        aria-controls="mobile-menu"
        onClick={() => setMenuOpen((open) => !open)}
      >
        <span className="hamburger-icon" aria-hidden="true">&#9776;</span>
      </button>

      {/* Menú móvil */}
      {menuOpen && (
        <>
          <div id="mobile-menu" className="mobile-menu" role="menu">
            {!isAuthenticated ? (
              <>
                <Link
                  to="/register"
                  className="nav-btn"
                  onClick={() => setMenuOpen(false)}
                  role="menuitem"
                >
                  Registro
                </Link>
                <Link
                  to="/login"
                  className="nav-btn"
                  onClick={() => setMenuOpen(false)}
                  role="menuitem"
                >
                  Iniciar sesión
                </Link>
              </>
            ) : (
              <>
                <Link
                  to="/create-ad"
                  className="nav-btn"
                  onClick={() => setMenuOpen(false)}
                  role="menuitem"
                >
                  Crear anuncio
                </Link>
                <Link
                  to="/my-ads"
                  className="nav-btn"
                  onClick={() => setMenuOpen(false)}
                  role="menuitem"
                >
                  Mis anuncios
                </Link>
                <Link
                  to="/contact"
                  className="nav-btn"
                  onClick={() => setMenuOpen(false)}
                  role="menuitem"
                >
                  Contacto
                </Link>
                <button
                  className="nav-btn logout-btn"
                  onClick={handleLogout}
                  role="menuitem"
                >
                  Cerrar sesión
                </button>
              </>
            )}
          </div>

          {/* Fondo para cerrar el menú al pulsar fuera */}
          <div className="menu-backdrop" onClick={handleBackdropClick} />
        </>
      )}
    </header>
  );
};

export default Header;
