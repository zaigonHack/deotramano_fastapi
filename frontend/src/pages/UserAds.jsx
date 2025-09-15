// src/pages/UserAds.jsx
import React, { useEffect, useState, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import "../styles/RegisterForm.css";
import BackButton from "../components/BackButton";
import Icon from "../components/Icon";
import { API_URL } from "../config";

const API = (API_URL || "").replace(/\/+$/, ""); // "" => mismo origen
const toImg = (p) => (p?.startsWith("http") ? p : `${API}${p}`);
const imageUrl = toImg;
const MAX_IMAGES = 9;

const UserAds = () => {
  const { user, isAuthenticated } = useAuth();
  const [ads, setAds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [editId, setEditId] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editError, setEditError] = useState("");
  const [editSuccess, setEditSuccess] = useState("");
  const [newImages, setNewImages] = useState([]);
  const [modalImg, setModalImg] = useState(null);
  const [preview, setPreview] = useState([]);
  const fileInputRef = useRef();

  // Token y headers de autorización para TODAS las requests
  const token =
    (typeof window !== "undefined" && localStorage.getItem("token")) || "";
  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

  // Cargar anuncios del usuario
  const loadAds = async () => {
    setLoading(true);
    setErr("");

    try {
      const response = await fetch(`${API}/api/ads/user/${user.id}`, {
        headers: {
          ...authHeaders,
          Accept: "application/json",
        },
        credentials: "include",
      });

      if (response.status === 403) {
        // Usuario bloqueado por admin
        setErr("Tu cuenta está bloqueada y no puedes ver/gestionar anuncios.");
        setAds([]);
        return;
      }
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setAds(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error cargando anuncios:", error);
      setErr(`Error al cargar anuncios: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isAuthenticated || !user?.id) {
      setLoading(false);
      return;
    }
    loadAds();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, user?.id]);

  // Iniciar edición
  const startEdit = (ad) => {
    setEditId(ad.id);
    setEditTitle(ad.title || "");
    setEditDesc(ad.description || "");
    setNewImages([]);
    setPreview([]);
    setEditError("");
    setEditSuccess("");
  };

  // Añadir nuevas imágenes (preview)
  const handleImageChange = (e) => {
    setEditError("");
    let files = Array.from(e.target.files);
    if (files.length + newImages.length > MAX_IMAGES) {
      setEditError(`Solo puedes añadir hasta ${MAX_IMAGES} imágenes`);
      return;
    }
    files = files.filter((file) => file.type.startsWith("image/"));
    setNewImages((prev) => [...prev, ...files]);
    files.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (ev) =>
        setPreview((prevPrev) => [...prevPrev, ev.target.result]);
      reader.readAsDataURL(file);
    });
    e.target.value = "";
  };

  const handleRemoveNewImage = (idx) => {
    setNewImages((imgs) => imgs.filter((_, i) => i !== idx));
    setPreview((prev) => prev.filter((_, i) => i !== idx));
  };

  // Eliminar imagen EXISTENTE (del backend)
  const handleRemoveExistingImage = async (adId, imageId) => {
    try {
      const resp = await fetch(`${API}/api/ads/delete-image/${imageId}`, {
        method: "DELETE",
        headers: {
          ...authHeaders,
          Accept: "application/json",
        },
        credentials: "include",
      });
      if (resp.status === 403) {
        setEditError(
          "No puedes eliminar imágenes: Este anuncio está en revisión y permanecerá bloqueado hasta su aprobación."
        );
        return;
      }
      if (!resp.ok) throw new Error(`Error ${resp.status}`);
      loadAds();
    } catch (error) {
      console.error("Error eliminando imagen:", error);
      setEditError("Error al eliminar imagen");
    }
  };

  // Eliminar TODAS las imágenes
  const handleRemoveAll = async (adId) => {
    try {
      const resp = await fetch(`${API}/api/ads/delete-all-images/${adId}`, {
        method: "DELETE",
        headers: {
          ...authHeaders,
          Accept: "application/json",
        },
        credentials: "include",
      });
      if (resp.status === 403) {
        setEditError(
          "No puedes eliminar imágenes: Este anuncio está en revisión y permanecerá bloqueado hasta su aprobación."
        );
        return;
      }
      if (!resp.ok) throw new Error(`Error ${resp.status}`);
      loadAds();
    } catch (error) {
      console.error("Error eliminando todas las imágenes:", error);
      setEditError("Error al eliminar imágenes");
    }
  };

  // Guardar edición (título, descripción y nuevas imágenes)
  const handleEdit = async (adId) => {
    setEditError("");
    setEditSuccess("");
    try {
      const formData = new FormData();
      formData.append("title", editTitle);
      formData.append("description", editDesc);
      newImages.forEach((img) => formData.append("new_images", img));

      const resp = await fetch(`${API}/api/ads/edit/${adId}`, {
        method: "PUT",
        body: formData,
        headers: {
          ...authHeaders, // NO añadas Content-Type con FormData
        },
        credentials: "include",
      });

      if (resp.status === 403) {
        setEditError(
          "No puedes editar: Este anuncio está en revisión y permanecerá bloqueado hasta su aprobación."
        );
        return;
      }

      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({}));
        throw new Error(errorData.detail || `Error ${resp.status}`);
      }

      setEditSuccess("¡Actualizado!");
      setEditId(null);
      setNewImages([]);
      setPreview([]);
      loadAds();
    } catch (error) {
      console.error("Error editando:", error);
      setEditError(`No se pudo actualizar: ${error.message}`);
    }
  };

  // Eliminar anuncio completo
  const handleDelete = async (adId) => {
    if (!window.confirm("¿Seguro que quieres eliminar este anuncio?")) return;

    try {
      const response = await fetch(`${API}/api/ads/delete/${adId}`, {
        method: "DELETE",
        headers: {
          ...authHeaders,
          Accept: "application/json",
        },
        credentials: "include",
      });

      if (response.status === 403) {
        setErr("No puedes borrar anuncios: tu cuenta está bloqueada.");
        return;
      }
      if (response.ok) {
        loadAds();
      } else {
        throw new Error(`Error ${response.status}`);
      }
    } catch (error) {
      console.error("Error eliminando anuncio:", error);
      setErr("Error al eliminar anuncio");
    }
  };

  // Modal de zoom
  const openModal = (img) => setModalImg(img);
  const closeModal = () => setModalImg(null);

  if (!isAuthenticated) {
    return (
      <div className="form-container">
        <BackButton label="Volver" />
        <div className="error-message">Inicia sesión para ver tus anuncios.</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="form-container">
        <BackButton label="Volver" />
        <h2 className="form-title">Mis anuncios</h2>
        <div style={{ textAlign: "center", padding: "2rem", color: "#0077cc" }}>
          <div>Cargando anuncios...</div>
          <div style={{ fontSize: "0.9em", marginTop: "0.5rem", color: "#666" }}>
            Usuario: {user?.id || "No identificado"}
          </div>
        </div>
      </div>
    );
  }

  if (err) {
    return (
      <div className="form-container">
        <BackButton label="Volver" />
        <h2 className="form-title">Mis anuncios</h2>
        <div className="error-message" style={{ margin: "1rem 0" }}>
          {err}
        </div>
        <button className="form-button" onClick={loadAds} style={{ margin: "1rem 0" }}>
          🔄 Reintentar
        </button>
        <div style={{ fontSize: "0.9em", color: "#666", marginTop: "1rem" }}>
          <strong>Debug info:</strong>
          <br />
          API URL: {API || "(mismo origen)"}
          <br />
          Usuario ID: {user?.id}
          <br />
          Autenticado: {isAuthenticated ? "Sí" : "No"}
        </div>
      </div>
    );
  }

  if (ads.length === 0) {
    return (
      <div className="form-container">
        <BackButton label="Volver" />
        <h2 className="form-title">Mis anuncios</h2>
        <div style={{ textAlign: "center", padding: "2rem" }}>
          <p style={{ color: "#666", marginBottom: "1.5rem" }}>
            No tienes anuncios aún.
          </p>
          <div style={{ fontSize: "0.9em", color: "#999", marginBottom: "1.5rem" }}>
            Usuario: {user?.email || user?.id}
          </div>
          <button
            className="form-button"
            onClick={() => (window.location.href = "/create-ad")}
            style={{ padding: "0.75rem 1.5rem" }}
          >
            ➕ Crear primer anuncio
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="form-container">
      <BackButton label="Volver" />
      <h2 className="form-title">Mis anuncios ({ads.length})</h2>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
          gap: "2rem",
          margin: "2rem 0",
        }}
      >
        {ads.map((ad) => (
          <div
            key={ad.id}
            className="ad-card"
            style={{
              border: "1px solid #eee",
              borderRadius: 14,
              padding: 18,
              background: "#fafbfc",
              boxShadow: "0 2px 10px rgba(0,0,34,0.08)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            {/* IMÁGENES EXISTENTES */}
            <div style={{ width: "100%", textAlign: "center", marginBottom: 8 }}>
              {ad.images && ad.images.length > 0 ? (
                <div
                  style={{
                    display: "flex",
                    gap: 4,
                    flexWrap: "wrap",
                    justifyContent: "center",
                  }}
                >
                  {ad.images.map((img, i) => (
                    <div key={img.id || i} className="img-thumb" style={{ margin: "0 3px" }}>
                      <img
                        src={imageUrl(img.url)}
                        alt={ad.title}
                        style={{
                          width: 82,
                          height: 62,
                          objectFit: "cover",
                          borderRadius: 6,
                          cursor: "zoom-in",
                          border: "1px solid #ddd",
                        }}
                        onClick={() => openModal(imageUrl(img.url))}
                        title="Haz clic para ver grande"
                        onError={(e) => {
                          e.currentTarget.style.opacity = "0.3";
                          e.currentTarget.title = "Error al cargar imagen";
                        }}
                      />

                      {editId === ad.id && (
                        <button
                          type="button"
                          className="img-x"
                          title="Quitar foto"
                          onClick={(ev) => {
                            ev.stopPropagation();
                            handleRemoveExistingImage(ad.id, img.id);
                          }}
                        >
                          <Icon name="close" size={14} className="spin-on-hover" />
                        </button>
                      )}
                    </div>
                  ))}

                  {editId === ad.id && ad.images.length > 0 && (
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
                        marginLeft: 7,
                      }}
                      onClick={() => handleRemoveAll(ad.id)}
                      title="Quitar todas las imágenes"
                    >
                      Quitar todas
                    </button>
                  )}
                </div>
              ) : (
                <div
                  style={{
                    width: 110,
                    height: 66,
                    background: "#e3eaf2",
                    borderRadius: 8,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#aaa",
                    margin: "0 auto",
                  }}
                >
                  Sin fotos
                </div>
              )}

              {/* PREVIEW DE NUEVAS IMÁGENES (sólo en edición) */}
              {editId === ad.id && preview.length > 0 && (
                <div
                  style={{
                    display: "flex",
                    gap: 10,
                    flexWrap: "wrap",
                    justifyContent: "center",
                    marginTop: 10,
                  }}
                >
                  {preview.map((img, idx) => (
                    <div key={idx} className="img-thumb">
                      <img
                        src={img}
                        alt={`preview-${idx}`}
                        style={{
                          width: 82,
                          height: 62,
                          objectFit: "cover",
                          borderRadius: 6,
                          cursor: "zoom-in",
                          border: "1.5px solid #0077cc",
                        }}
                        onClick={() => openModal(img)}
                        title="Haz clic para ver grande"
                      />
                      <button
                        type="button"
                        className="img-x"
                        title="Quitar nueva foto"
                        onClick={() => handleRemoveNewImage(idx)}
                      >
                        <Icon name="close" size={14} className="spin-on-hover" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* INPUT PARA NUEVAS FOTOS (sólo en edición) */}
              {editId === ad.id &&
                ad.images.length + newImages.length < MAX_IMAGES && (
                  <div style={{ marginTop: 12 }}>
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      accept="image/*"
                      style={{ display: "none" }}
                      onChange={handleImageChange}
                    />
                    <button
                      className="form-button"
                      type="button"
                      style={{
                        background: "#0077cc",
                        color: "#fff",
                        borderRadius: 7,
                        marginTop: 4,
                        fontWeight: 500,
                        padding: "7px 16px",
                      }}
                      onClick={() => fileInputRef.current.click()}
                    >
                      📷 Añadir fotos ({ad.images.length + newImages.length}/
                      {MAX_IMAGES})
                    </button>
                  </div>
                )}
            </div>

            {/* FORMULARIO DE EDICIÓN */}
            {editId === ad.id ? (
              <div style={{ width: "100%" }}>
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  placeholder="Título del anuncio"
                  maxLength={60}
                  style={{
                    width: "100%",
                    marginBottom: 8,
                    fontSize: "1.10em",
                    fontWeight: 600,
                    borderRadius: 6,
                    border: "1px solid #c7daf0",
                    padding: "7px 10px",
                  }}
                />
                <textarea
                  value={editDesc}
                  onChange={(e) => setEditDesc(e.target.value)}
                  placeholder="Descripción del anuncio"
                  maxLength={500}
                  style={{
                    width: "100%",
                    minHeight: 65,
                    fontSize: "1em",
                    borderRadius: 6,
                    border: "1px solid #c7daf0",
                    padding: "7px 10px",
                    resize: "vertical",
                  }}
                />
                <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                  <button
                    className="form-button"
                    style={{ background: "#0077cc", color: "#fff", fontWeight: 500 }}
                    onClick={() => handleEdit(ad.id)}
                    disabled={!editTitle.trim() || !editDesc.trim()}
                  >
                    💾 Guardar
                  </button>
                  <button
                    className="form-button"
                    style={{ background: "#ddd", color: "#111" }}
                    onClick={() => {
                      setEditId(null);
                      setNewImages([]);
                      setPreview([]);
                      setEditError("");
                      setEditSuccess("");
                    }}
                  >
                    ❌ Cancelar
                  </button>
                </div>
                {editError && (
                  <div className="error-message" style={{ marginTop: "0.5rem" }}>
                    {editError}
                  </div>
                )}
                {editSuccess && (
                  <div className="success-message" style={{ marginTop: "0.5rem" }}>
                    {editSuccess}
                  </div>
                )}
              </div>
            ) : (
              <>
                {/* TÍTULO Y DESCRIPCIÓN */}
                <div
                  style={{
                    fontWeight: 700,
                    fontSize: "1.26em",
                    margin: "13px 0 4px 0",
                    color: "#203040",
                    letterSpacing: ".01em",
                    textAlign: "center",
                    lineHeight: "1.18",
                  }}
                >
                  {ad.title || "Sin título"}
                </div>
                <div
                  style={{
                    color: "#444",
                    fontSize: "1.01em",
                    minHeight: 44,
                    textAlign: "center",
                    lineHeight: "1.4",
                    padding: "0 0.5rem",
                  }}
                >
                  {ad.description || "Sin descripción"}
                </div>
              </>
            )}

            {/* BOTONES DE ACCIÓN */}
            {editId !== ad.id && (
              <div style={{ marginTop: 18, display: "flex", gap: 10 }}>
                <button
                  className="form-button"
                  style={{
                    background: "#0077cc",
                    color: "#fff",
                    fontWeight: 500,
                    fontSize: "1em",
                  }}
                  onClick={() => startEdit(ad)}
                >
                  ✏️ Editar
                </button>
                <button
                  className="form-button"
                  style={{
                    background: "#f44336",
                    color: "#fff",
                    fontWeight: 500,
                    fontSize: "1em",
                  }}
                  onClick={() => handleDelete(ad.id)}
                >
                  🗑️ Borrar
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* BOTÓN PARA CREAR NUEVO ANUNCIO */}
      <div style={{ textAlign: "center", marginTop: "2rem" }}>
        <button
          className="form-button"
          onClick={() => (window.location.href = "/create-ad")}
          style={{
            background: "#28a745",
            color: "white",
            padding: "0.75rem 1.5rem",
            fontSize: "1.1rem",
          }}
        >
          ➕ Crear nuevo anuncio
        </button>
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
              borderRadius: 14,
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

export default UserAds;
