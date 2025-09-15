// src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import RegisterForm from './components/RegisterForm';
import LoginForm from './components/LoginForm';
import ForgotPassword from './components/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import Dashboard from './Dashboard';
import CreateAd from './pages/CreateAd';
import UserAds from './pages/UserAds';
import AdminPanel from './pages/AdminPanel';
import ChangePassword from "./pages/ChangePassword";
import Contact from "./pages/Contact";            // 👈 AÑADIDO

function App() {
  return (
    <Router>
      <Header />
      <div className="header-space" />
      <main className="form-wrapper">
        <Routes>
          <Route path="/" element={<RegisterForm />} />
          <Route path="/register" element={<RegisterForm />} />
          <Route path="/login" element={<LoginForm />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/create-ad" element={<CreateAd />} />
          <Route path="/my-ads" element={<UserAds />} />
          <Route path="/admin" element={<AdminPanel />} />
          <Route path="/change-password" element={<ChangePassword />} />
          <Route path="/contact" element={<Contact />} />   {/* 👈 NUEVA RUTA */}
        </Routes>
      </main>
      <Footer />
    </Router>
  );
}

export default App;
