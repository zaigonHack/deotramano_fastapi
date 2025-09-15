// src/components/Footer.jsx
import React from "react";
import "../styles/RegisterForm.css"; // Tu CSS global ya tiene el footer

const Footer = () => (
  <footer className="main-footer">
    <div className="footer-content">
      © {new Date().getFullYear()} DeOtraMano &middot; Todos los derechos reservados
    </div>
  </footer>
);

export default Footer;

