// src/pages/AdminDashboard.jsx
import React, { useEffect, useState, useMemo } from "react";
import { API_URL } from "../config";
import { useAuth } from "../context/AuthContext";
import "../styles/Admin.css";
import Icon from "../components/Icon";

const AdminDashboard = () => {
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [ads, setAds] = useState([]);

  // Token para endpoints protegidos de admin
  const token = useMemo(
    () => (typeof window !== "undefined" ? localStorage.getItem("token") || "" : ""),
    []
  );
  const authHeaders = useMemo(
    () => (token ? { Authorization: `Bearer ${token}` } : {}),
    [token]
  );

  // Cargar usuarios y anuncios
  useEffect(() => {
    // Usuarios
    fetch(`${API_URL}/api/admin/users`, {
      headers: {
        Accept: "application/json",
        ...authHeaders,
      },
      credentials: "include",
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => setUsers(Array.isArray(data) ? data : []))
      .catch((err) => {
        console.error("Error cargando usuarios:", err);
        setUsers([]);
      });

    // Anuncios
    fetch(`${API_URL}/api/admin/ads`, {
      headers: {
        Accept: "application/json",
        ...authHeaders,
      },
      credentials: "include",
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => setAds(Array.isArray(data) ? data : []))
      .catch((err) => {
        console.error("Error cargando anuncios:", err);
        setAds([]);
      });
  }, [API_URL, authHeaders]);

  // Eliminar anuncio completo
  const deleteAd = (id) => {
    fetch(`${API_URL}/api/admin/ads/${id}`, {
      method: "DELETE",
      headers: {
        Accept: "application/json",
        ...authHeaders,
      },
      credentials: "include",
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setAds((ads) => ads.filter((a) => a.id !== id));
      })
      .catch((err) => console.error("Error eliminando anuncio:", err));
  };

  // Eliminar usuario
  const deleteUser = (id) => {
    fetch(`${API_URL}/api/admin/users/${id}`, {
      method: "DELETE",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...authHeaders,
      },
      credentials: "include",
      // Si quieres borrar administradores, el backend pide admin_password en body
      // body: JSON.stringify({ admin_password: "..." })
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setUsers((users) => users.filter((u) => u.id !== id));
      })
      .catch((err) => console.error("Error eliminando usuario:", err));
  };

  // Eliminar UNA imagen de un anuncio (endpoint admin)
  const deleteAdImage = (adId, imageId) => {
    fetch(`${API_URL}/api/admin/ads/${adId}/images/${imageId}`, {
      method: "DELETE",
      headers: {
        Accept: "application/json",
        ...authHeaders,
      },
      credentials: "include",
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        // Refrescar estado local: quitar la imagen de ese anuncio
        setAds((ads) =>
          ads.map((ad) =>
            ad.id === adId
              ? { ...ad, images: (ad.images || []).filter((im) => im.id !== imageId) }
              : ad
          )
        );
      })
      .catch((err) => console.error("Error eliminando imagen:", err));
  };

  return (
    <div className="admin-container">
      <h1>Panel de Administración</h1>

      <section>
        <h2>Usuarios</h2>
        <div className="flex-list">
          {users.map((u) => (
            <div key={u.id} className="card">
              <p>
                <b>
                  {u.name} {u.surname}
                </b>
              </p>
              <p>{u.email}</p>
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <button className="form-button" onClick={() => deleteUser(u.id)}>
                  Eliminar
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2>Anuncios</h2>
        <div className="flex-list">
          {ads.map((ad) => (
            <div key={ad.id} className="card">
              <h3>{ad.title}</h3>
              <p>{ad.description}</p>
              <p>
                <i>{ad.user_email}</i>
              </p>

              {/* Galería con botón X que gira al hover */}
              <div className="images" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {(ad.images || []).map((im) => (
                  <div key={im.id} className="img-thumb">
                    <img
                      src={im.url?.startsWith("http") ? im.url : `${API_URL}${im.url}`}
                      alt=""
                      style={{
                        width: 82,
                        height: 62,
                        objectFit: "cover",
                        borderRadius: 6,
                        border: "1px solid #ddd",
                        display: "block",
                      }}
                    />
                    <button
                      type="button"
                      className="img-x"
                      title="Eliminar imagen"
                      onClick={() => deleteAdImage(ad.id, im.id)}
                    >
                      {/* Gira por CSS (.spin-on-hover) */}
                      <Icon name="close" size={14} className="spin-on-hover" />
                    </button>
                  </div>
                ))}
              </div>

              <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                <button className="form-button" onClick={() => deleteAd(ad.id)}>
                  Eliminar anuncio
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default AdminDashboard;
