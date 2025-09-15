// src/pages/CreateAd.jsx
import React, { useState, useRef, useEffect } from "react";
import BackButton from "../components/BackButton";
import "../styles/RegisterForm.css";
import { useAuth } from "../context/AuthContext";
import Icon from "../components/Icon";
import { useNavigate } from "react-router-dom";
import { API_URL } from "../config";

const MAX_IMAGES = 9;
const TITLE_MAX = 60;
const DESC_MAX = 500;

// BASE del backend:
// - En dev: viene de VITE_API_URL (http://127.0.0.1:8000)
// - En prod: queda "" y usamos rutas relativas
const BASE = (API_URL || "").replace(/\/$/, "");
const API = BASE || ""; // si está vacío => mismo host (Railway)

const CreateAd = () => {
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [images, setImages] = useState([]);
  const [preview, setPreview] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [modalImg, setModalImg] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [createdUrls, setCreatedUrls] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [countdown, setCountdown] = useState(null);
  const fileInputRef = useRef();
  const { user } = useAuth();
  const navigate = useNavigate();

  // --- Auth token (Bearer) ---
  const token =
    (typeof window !== "undefined" && localStorage.getItem("token")) || "";
  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

  // --- Efecto cuenta atrás (redirige al llegar a 0) ---
  useEffect(() => {
    if (countdown === null) return; // no activo
    if (countdown <= 0) {
      navigate("/my-ads");
      return;
    }
    const t = setTimeout(() => setCountdown((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown, navigate]);

  // --- Drag & Drop handlers ---
  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    setError("");
    setSuccess("");
    let files = Array.from(e.dataTransfer.files);
    if (files.length + images.length > MAX_IMAGES) {
      setError(`Solo puedes subir hasta ${MAX_IMAGES} imágenes`);
      return;
    }
    files = files.filter((file) => file.type.startsWith("image/"));
    setImages((prev) => [...prev, ...files]);
    files.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (ev) =>
        setPreview((prevPrev) => [...prevPrev, ev.target.result]);
      reader.readAsDataURL(file);
    });
  };
  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };
  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  // --- Input handler ---
  const handleImageChange = (e) => {
    setError("");
    setSuccess("");
    let files = Array.from(e.target.files);
    if (files.length + images.length > MAX_IMAGES) {
      setError(`Solo puedes subir hasta ${MAX_IMAGES} imágenes`);
      return;
    }
    files = files.filter((file) => file.type.startsWith("image/"));
    setImages((prev) => [...prev, ...files]);
    files.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (ev) =>
        setPreview((prevPrev) => [...prevPrev, ev.target.result]);
      reader.readAsDataURL(file);
    });
    e.target.value = ""; // reset input para poder elegir la misma
  };

  // --- Quitar imágenes ---
  const handleRemoveImage = (idx) => {
    setImages((imgs) => imgs.filter((_, i) => i !== idx));
    setPreview((prev) => prev.filter((_, i) => i !== idx));
  };
  const handleRemoveAll = () => {
    setImages([]);
    setPreview([]);
    setError("");
    setSuccess("");
  };

  // --- Modal Zoom (foto grande) ---
  const openModal = (img) => setModalImg(img);
  const closeModal = () => setModalImg(null);

  // --- Subida REAL ---
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setError("");
    setSuccess("");
    setCreatedUrls([]);
    setCountdown(null);

    if (!token) {
      setError("Debes iniciar sesión para crear anuncios.");
      return;
    }
    if (!user?.id) {
      setError("No se encontró el usuario. Inicia sesión.");
      return;
    }
    if (!title.trim() || !desc.trim()) {
      setError("Pon título y descripción");
      return;
    }
    if (images.length === 0) {
      setError("Sube al menos una imagen");
      return;
    }

    const formData = new FormData();
    formData.append("title", title);
    formData.append("description", desc);
    formData.append("user_id", user.id); // id del user logueado
    images.forEach((img) => formData.append("images", img));

    try {
      setSubmitting(true);
      const resp = await fetch(`${API}/api/ads/create`, {
        method: "POST",
        body: formData,
        headers: {
          ...authHeaders, // Authorization: Bearer xxx
          // IMPORTANTE: no pongas Content-Type aquí; fetch lo calcula con boundary
        },
        credentials: "include", // por si usas cookie de sesión
      });

      const text = await resp.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        // mantiene data como {}
      }

      if (!resp.ok) {
        // Intenta sacar un mensaje legible aunque llegue un objeto "detail"
        let msg =
          (typeof data?.detail === "string" && data.detail) ||
          data?.message ||
          (resp.status === 401
            ? "No autenticado. Inicia sesión de nuevo."
            : resp.status === 422
            ? "Datos inválidos. Revisa título, descripción e imágenes."
            : `Error ${resp.status}`);
        if (typeof data?.detail === "object" && data.detail?.msg) {
          msg = data.detail.msg;
        }
        setError(String(msg));
        return;
      }

      // data.image_urls es un array de rutas tipo "/static/images/xxx.jpg"
      const absUrls = Array.isArray(data.image_urls)
        ? data.image_urls.map((u) => (u?.startsWith("http") ? u : `${API}${u}`))
        : [];

      // ✅ Mensaje claro de revisión
      const notice =
        "¡Anuncio enviado! Tu anuncio ha sido enviado a revisión. " +
        "Un moderador lo aprobará en breve y estará disponible en unos minutos.";

      setSuccess(notice);
      setTitle("");
      setDesc("");
      setImages([]);
      setPreview([]);
      setCreatedUrls(absUrls);

      // ⏱ Aviso 10 s con contador y luego redirige
      setCountdown(10);
    } catch (err) {
      setError("Error de conexión");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="form-wrapper">
      <div className="form-container">
        {/* BOTÓN VOLVER DENTRO DEL CUADRO */}
        <BackButton label="Volver" />
        <h2 className="form-title">Añadir anuncio</h2>
        <form
          onSubmit={handleSubmit}
          className="register-form"
          style={{ margin: 0, padding: 0 }}
        >
          <label htmlFor="title" className="form-label">
            Título
            <span
              style={{
                color: "#bbb",
                fontWeight: 400,
                marginLeft: 6,
                fontSize: "0.96em",
              }}
            >
              (máx {TITLE_MAX} caracteres)
            </span>
          </label>
          <input
            className="form-input"
            type="text"
            maxLength={TITLE_MAX}
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Ej: Bici de montaña"
            required
          />
          {/* Contador de caracteres título */}
          <div
            style={{
              textAlign: "right",
              marginTop: 4,
              marginBottom: 10,
              fontSize: "0.86rem",
              color: title.length > TITLE_MAX * 0.9 ? "#c0392b" : "#888",
            }}
            aria-live="polite"
          >
            {TITLE_MAX - title.length} caracteres restantes
          </div>

          <label htmlFor="description" className="form-label">
            Descripción
            <span
              style={{
                color: "#bbb",
                fontWeight: 400,
                marginLeft: 6,
                fontSize: "0.96em",
              }}
            >
              (cuenta lo importante, máx {DESC_MAX})
            </span>
          </label>
          <textarea
            className="form-input"
            id="description"
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            maxLength={DESC_MAX}
            required
            style={{
              minHeight: 120,
              width: "100%",
              resize: "vertical",
              fontSize: "1rem",
              marginBottom: 6,
            }}
            placeholder="Describe tu anuncio..."
          />
          {/* Contador de caracteres descripción */}
          <div
            style={{
              textAlign: "right",
              marginBottom: "1rem",
              fontSize: "0.86rem",
              color: desc.length > DESC_MAX * 0.9 ? "#c0392b" : "#888",
            }}
            aria-live="polite"
          >
            {DESC_MAX - desc.length} caracteres restantes
          </div>

          <label className="form-label" style={{ marginBottom: 5 }}>
            Fotos (máx {MAX_IMAGES})
          </label>
          <div
            className={`drop-area ${dragActive ? "drag-active" : ""}`}
            style={{
              border: dragActive ? "2px solid #36c" : "2px dashed #0077cc",
              borderRadius: 10,
              padding: 16,
              textAlign: "center",
              background: dragActive ? "#e7f1ff" : "#f6f8fa",
              marginBottom: 18,
              cursor: "pointer",
              position: "relative",
              minHeight: 85,
              outline: "none",
              transition: "box-shadow 0.18s",
              userSelect: "none",
            }}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current.click()}
            tabIndex={0}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*"
              style={{ display: "none" }}
              onChange={handleImageChange}
              disabled={images.length >= MAX_IMAGES}
            />
            {/* ICONO FOTO */}
            <svg
              width="38"
              height="38"
              viewBox="0 0 48 48"
              fill="none"
              style={{ marginBottom: 6, opacity: 0.42 }}
            >
              <rect
                x="6"
                y="14"
                width="36"
                height="24"
                rx="3"
                stroke="#0077cc"
                strokeWidth="2"
                fill="#fff"
              />
              <circle cx="17" cy="26" r="3.2" fill="#0077cc" />
              <path
                d="M9 33l7-7c1.4-1.3 3.6-1.3 5 0l6 6c1.4-1.3 3.6-1.3 5 0l7-7"
                stroke="#0077cc"
                strokeWidth="2"
                fill="none"
              />
            </svg>
            <div
              style={{
                color: "#0077cc",
                fontWeight: 500,
                marginBottom: 2,
                fontSize: "1.09em",
              }}
            >
              Arrastra imágenes aquí o haz clic para seleccionar
            </div>
            <div style={{ fontSize: "0.93em", color: "#999" }}>
              JPG, PNG, hasta {MAX_IMAGES} imágenes
            </div>
          </div>

          {/* Previsualización */}
          {preview.length > 0 && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(84px, 1fr))",
                gap: 14,
                margin: "14px 0",
                justifyItems: "center",
              }}
            >
              {preview.map((img, idx) => (
                <div key={idx} className="img-thumb">
                  <img
                    src={img}
                    alt={`preview-${idx}`}
                    style={{
                      width: 84,
                      height: 84,
                      objectFit: "cover",
                      borderRadius: 8,
                      border: "1.5px solid #0077cc",
                      boxShadow: "0 2px 7px rgba(30,30,60,0.08)",
                      cursor: "zoom-in",
                      transition: "transform 0.18s",
                    }}
                    onClick={() => openModal(img)}
                    title="Haz clic para ver grande"
                  />

                  <button
                    type="button"
                    className="img-x"
                    title="Quitar foto"
                    onClick={(ev) => {
                      ev.stopPropagation();
                      handleRemoveImage(idx);
                    }}
                  >
                    <Icon name="close" size={14} className="spin-on-hover" />
                  </button>
                </div>
              ))}

              {preview.length > 1 && (
                <button
                  type="button"
                  className="form-button"
                  style={{
                    background: "#eee",
                    color: "#0077cc",
                    minHeight: 36,
                    minWidth: 40,
                    borderRadius: 8,
                    fontWeight: "bold",
                    gridColumn: "1 / -1",
                    marginTop: 4,
                  }}
                  onClick={handleRemoveAll}
                  title="Quitar todas las imágenes"
                >
                  Quitar todas
                </button>
              )}
            </div>
          )}

          {error && <div className="error-message">{error}</div>}
          {success && (
            <div className="success-message">
              {success}
              {countdown !== null && (
                <div style={{ marginTop: 6 }}>
                  Redirigiendo en {countdown}…
                </div>
              )}
            </div>
          )}

          <button
            className="form-button"
            type="submit"
            style={{ marginTop: 22, fontSize: "1.12rem" }}
            disabled={submitting}
          >
            {submitting ? "Enviando…" : "Crear anuncio"}
          </button>
        </form>

        {/* GALERÍA de imágenes subidas con modal */}
        {createdUrls.length > 0 && (
          <div style={{ marginTop: 18 }}>
            <div
              style={{
                fontWeight: 600,
                marginBottom: 8,
                color: "#1976d2",
                textAlign: "center",
              }}
            >
              Imágenes subidas:
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))",
                gap: 12,
                alignItems: "start",
              }}
            >
              {createdUrls.map((u, i) => (
                <div
                  key={i}
                  onClick={() => openModal(u)}
                  title="Haz clic para ver grande"
                  style={{
                    display: "block",
                    border: "1px solid #ddd",
                    borderRadius: 8,
                    overflow: "hidden",
                    boxShadow: "0 2px 7px rgba(30,30,60,0.08)",
                    cursor: "zoom-in",
                  }}
                >
                  <img
                    src={u}
                    alt={`uploaded-${i}`}
                    style={{
                      width: "100%",
                      height: 110,
                      objectFit: "cover",
                      display: "block",
                    }}
                    onError={(e) => (e.currentTarget.style.opacity = "0.35")}
                  />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* MODAL para zoom de imagen */}
      {modalImg && (
        <div
          style={{
            position: "fixed",
            zIndex: 4000,
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(30,30,40,0.78)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "zoom-out",
          }}
          onClick={closeModal}
        >
          <img
            src={modalImg}
            alt="Zoom"
            style={{
              maxWidth: "92vw",
              maxHeight: "80vh",
              borderRadius: 12,
              boxShadow: "0 6px 30px rgba(30,30,60,0.30)",
              border: '2.5px solid #fff',
              background: "#fff",
            }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
};

export default CreateAd;
