// src/pages/AdminPanel.jsx
import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { API_URL } from "../config";
import "../styles/RegisterForm.css";
import "../styles/Admin.css";
import Icon from "../components/Icon";

// Acepta string o objeto { url: "..."}
const toImg = (v) => {
  if (!v) return "";
  if (typeof v === "string") return v.startsWith("http") ? v : `${API_URL}${v}`;
  if (typeof v === "object" && v.url) {
    return v.url.startsWith("http") ? v.url : `${API_URL}${v.url}`;
  }
  return "";
};

const AdminPanel = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const token = useMemo(() => localStorage.getItem("token") || "", []);
  const authHeaders = useMemo(
    () => (token ? { Authorization: `Bearer ${token}` } : {}),
    [token]
  );

  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [users, setUsers] = useState([]);
  const [ads, setAds] = useState([]);

  // UI extra
  const [qUser, setQUser] = useState("");
  const [qAd, setQAd] = useState("");
  const [zoomSrc, setZoomSrc] = useState(null);

  // --- NUEVO: formularios de administración ---
  const [newAdminEmail, setNewAdminEmail] = useState("");
  const [newAdminPass, setNewAdminPass] = useState("");
  const [newAdminName, setNewAdminName] = useState("");
  const [newAdminSurname, setNewAdminSurname] = useState("");
  const [promoteEmail, setPromoteEmail] = useState("");
  const [busyCreate, setBusyCreate] = useState(false);
  const [busyPromote, setBusyPromote] = useState(false);

  const filteredUsers = useMemo(() => {
    const q = qUser.trim().toLowerCase();
    if (!q) return users;
    return users.filter(
      (u) =>
        `${u.name ?? ""} ${u.surname ?? ""}`.toLowerCase().includes(q) ||
        String(u.email ?? "").toLowerCase().includes(q)
    );
  }, [users, qUser]);

  const filteredAds = useMemo(() => {
    const q = qAd.trim().toLowerCase();
    if (!q) return ads;
    return ads.filter(
      (a) =>
        String(a.title ?? "").toLowerCase().includes(q) ||
        String(a.description ?? "").toLowerCase().includes(q) ||
        String(a.user_email ?? "").toLowerCase().includes(q)
    );
  }, [ads, qAd]);

  // --- helper de fetch con el mismo estilo que ya usabas ---
  async function fetchJSON(url, opts = {}) {
    const resp = await fetch(url, {
      credentials: "include",
      headers: {
        Accept: "application/json",
        ...(opts.body && typeof opts.body === "string"
          ? { "Content-Type": "application/json" }
          : {}),
        ...authHeaders,
        ...(opts.headers || {}),
      },
      ...opts,
    });

    if (resp.status === 401) throw new Error("No autenticado. Inicia sesión.");
    if (resp.status === 403)
      throw new Error("No autorizado (se requiere administrador).");

    const text = await resp.text();
    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch {}

    if (!resp.ok) {
      let msg = data?.detail || data?.message || `Error ${resp.status}`;
      if (Array.isArray(msg)) {
        msg = msg
          .map((e) => e?.msg || e?.detail || JSON.stringify(e))
          .join(" | ");
      } else if (typeof msg === "object") {
        msg = msg?.msg || msg?.detail || JSON.stringify(msg);
      }
      throw new Error(String(msg));
    }
    return data;
  }

  const loadAll = async () => {
    setLoading(true);
    setErr("");
    try {
      const [usersData, adsData] = await Promise.all([
        fetchJSON(`${API_URL}/api/admin/users`),
        fetchJSON(`${API_URL}/api/admin/ads`),
      ]);
      setUsers(Array.isArray(usersData) ? usersData : []);
      setAds(Array.isArray(adsData) ? adsData : []);
    } catch (e) {
      setErr(e.message || "No se pudo cargar el panel");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/login");
      return;
    }
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  // --------- USERS ----------
  const handleBlockUser = async (u) => {
    try {
      await fetchJSON(`${API_URL}/api/admin/users/${u.id}/block`, {
        method: "POST",
      });
      setUsers((prev) =>
        prev.map((x) => (x.id === u.id ? { ...x, is_blocked: true } : x))
      );
    } catch (e) {
      alert(e.message);
    }
  };

  const handleUnblockUser = async (u) => {
    try {
      await fetchJSON(`${API_URL}/api/admin/users/${u.id}/unblock`, {
        method: "POST",
      });
      setUsers((prev) =>
        prev.map((x) => (x.id === u.id ? { ...x, is_blocked: false } : x))
      );
    } catch (e) {
      alert(e.message);
    }
  };

  const handleSetPasswordForUser = async (u) => {
    const pwd1 = window.prompt(
      `Nueva contraseña para ${u.email} (mín. 8, mayúscula, minúscula, número y símbolo permitido):`
    );
    if (pwd1 == null) return;

    const pwd2 = window.prompt("Repite la nueva contraseña:");
    if (pwd2 == null) return;

    const newPassword = String(pwd1).trim();
    const newPasswordConfirm = String(pwd2).trim();

    if (newPassword !== newPasswordConfirm) {
      alert("La nueva contraseña y su confirmación no coinciden.");
      return;
    }

    const allowedSymbols = "!@#$%^&*()_-+=[]{}:;,.?~";
    const esc = (s) => s.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&");
    const re = new RegExp(
      `^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[${esc(allowedSymbols)}])[A-Za-z\\d${esc(
        allowedSymbols
      )}]{8,64}$`
    );
    if (!re.test(newPassword)) {
      alert(
        "Contraseña inválida.\nDebe tener entre 8 y 64 caracteres, incluir al menos una minúscula, una mayúscula, un número y uno de estos símbolos:\n" +
          allowedSymbols
      );
      return;
    }

    try {
      await fetchJSON(`${API_URL}/api/admin/users/${u.id}/set-password`, {
        method: "POST",
        body: JSON.stringify({
          new_password: newPassword,
          new_password_confirm: newPasswordConfirm,
        }),
      });
      alert("Contraseña cambiada correctamente.");
    } catch (e) {
      alert(e.message || "No se pudo cambiar la contraseña.");
    }
  };

  const handleDeleteUser = async (u) => {
    const sure = window.confirm(
      `¿Seguro que quieres eliminar al usuario "${u.email}"?\nEsto podría borrar sus anuncios asociados.`
    );
    if (!sure) return;

    let body = undefined;
    if (u.is_admin) {
      const pwd = window.prompt(
        "El usuario es ADMIN. Introduce tu contraseña de administrador para confirmar:"
      );
      if (!pwd) return;
      body = JSON.stringify({ admin_password: pwd });
    }

    try {
      await fetchJSON(`${API_URL}/api/admin/users/${u.id}`, {
        method: "DELETE",
        body,
      });
      setUsers((prev) => prev.filter((x) => x.id !== u.id));
      setAds((prev) => prev.filter((a) => a.user_email !== u.email));
    } catch (e) {
      alert(e.message);
    }
  };

  // --------- NUEVO: crear admin y promover admin ----------
  const handleCreateAdmin = async () => {
    const email = newAdminEmail.trim().toLowerCase();
    const name = newAdminName.trim() || "Admin";
    const surname = newAdminSurname.trim() || "User";
    const password = newAdminPass;

    if (!email || !password) {
      alert("Email y contraseña son obligatorios.");
      return;
    }
    setBusyCreate(true);
    try {
      await fetchJSON(`${API_URL}/api/admin/users/create-admin`, {
        method: "POST",
        body: JSON.stringify({ email, name, surname, password }),
      });
      alert("Administrador creado correctamente.");
      setNewAdminEmail("");
      setNewAdminPass("");
      setNewAdminName("");
      setNewAdminSurname("");
      await loadAll();
    } catch (e) {
      alert(e.message || "No se pudo crear el administrador.");
    } finally {
      setBusyCreate(false);
    }
  };

  const handlePromoteAdmin = async () => {
    const email = promoteEmail.trim().toLowerCase();
    if (!email) {
      alert("Indica el email del usuario a promover.");
      return;
    }
    setBusyPromote(true);
    try {
      await fetchJSON(`${API_URL}/api/admin/users/promote-admin`, {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      alert(`Usuario ${email} promovido a administrador.`);
      setPromoteEmail("");
      await loadAll();
    } catch (e) {
      alert(e.message || "No se pudo promover a administrador.");
    } finally {
      setBusyPromote(false);
    }
  };

  // --------- ADS ----------
  const handleDeleteAd = async (ad) => {
    const ok = window.confirm(
      `¿Seguro que quieres eliminar el anuncio "${ad.title ?? ad.id}"?`
    );
    if (!ok) return;
    try {
      await fetchJSON(`${API_URL}/api/admin/ads/${ad.id}`, { method: "DELETE" });
      setAds((prev) => prev.filter((x) => x.id !== ad.id));
    } catch (e) {
      alert(e.message);
    }
  };

  const handleBlockAd = async (ad) => {
    try {
      await fetchJSON(`${API_URL}/api/admin/ads/${ad.id}/block`, {
        method: "POST",
      });
    } catch (e) {
      alert(e.message);
      return;
    }
    setAds((prev) =>
      prev.map((x) => (x.id === ad.id ? { ...x, status: "review" } : x))
    );
  };

  const handleUnblockAd = async (ad) => {
    try {
      await fetchJSON(`${API_URL}/api/admin/ads/${ad.id}/unblock`, {
        method: "POST",
      });
    } catch (e) {
      alert(e.message);
      return;
    }
    setAds((prev) =>
      prev.map((x) => (x.id === ad.id ? { ...x, status: "active" } : x))
    );
  };

  const handleDeleteOneImage = async (adId, img) => {
    const imageId = typeof img === "object" ? img.id : null;
    if (!imageId) {
      alert("Esta imagen no tiene ID, no se puede eliminar individualmente.");
      return;
    }
    const ok = window.confirm("¿Eliminar esta imagen?");
    if (!ok) return;
    try {
      await fetchJSON(`${API_URL}/api/admin/ads/${adId}/images/${imageId}`, {
        method: "DELETE",
      });
      setAds((prev) =>
        prev.map((a) =>
          a.id === adId
            ? {
                ...a,
                images: (a.images || []).filter((x) =>
                  typeof x === "object" ? x.id !== imageId : true
                ),
              }
            : a
        )
      );
    } catch (e) {
      alert(e.message);
    }
  };

  if (loading) {
    return (
      <div className="form-container">
        <h2 className="form-title">Panel de Administración</h2>
        <div style={{ textAlign: "center", padding: "1.5rem", color: "#0077cc" }}>
          Cargando datos del panel…
        </div>
      </div>
    );
  }

  if (err) {
    return (
      <div className="form-container">
        <h2 className="form-title">Panel de Administración</h2>
        <div className="error-message" style={{ marginTop: 12 }}>
          {err}
        </div>
        <div style={{ textAlign: "center", marginTop: 14 }}>
          <button className="form-button" onClick={loadAll}>
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  const StatusBadge = ({ status }) => {
    const s = (status || "active").toLowerCase();
    const style =
      {
        active: { background: "#e8f5e9", color: "#2e7d32" },
        review: { background: "#fff8e1", color: "#8d6e63" },
        blocked: { background: "#ffebee", color: "#c62828" },
      }[s] || { background: "#eef3f9", color: "#607d8b" };
    return (
      <span
        style={{ ...style, padding: "2px 8px", borderRadius: 999, fontSize: ".8em" }}
      >
        {s}
      </span>
    );
  };

  return (
    <div className="form-container" style={{ maxWidth: 1100 }}>
      <h2 className="form-title">Panel de Administración</h2>

      {/* NUEVO: Acciones rápidas de administradores */}
      <section
        style={{
          marginTop: 6,
          background: "#ffffff",
          border: "1px solid #e5eaf0",
          borderRadius: 12,
          padding: 14,
          boxShadow: "0 2px 10px rgba(0,0,34,0.04)",
        }}
      >
        <h3 style={{ marginTop: 0, marginBottom: 10 }}>Administradores</h3>

        {/* Crear nuevo admin */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: 10,
            alignItems: "end",
            marginBottom: 12,
          }}
        >
          <input
            className="form-input"
            placeholder="Email nuevo admin"
            value={newAdminEmail}
            onChange={(e) => setNewAdminEmail(e.target.value)}
          />
          <input
            className="form-input"
            placeholder="Nombre (opcional)"
            value={newAdminName}
            onChange={(e) => setNewAdminName(e.target.value)}
          />
          <input
            className="form-input"
            placeholder="Apellidos (opcional)"
            value={newAdminSurname}
            onChange={(e) => setNewAdminSurname(e.target.value)}
          />
          <input
            className="form-input"
            type="password"
            placeholder="Contraseña fuerte"
            value={newAdminPass}
            onChange={(e) => setNewAdminPass(e.target.value)}
          />
          <button
            className="form-button"
            onClick={handleCreateAdmin}
            disabled={busyCreate}
            title="Crea un usuario administrador con email y contraseña"
          >
            {busyCreate ? "Creando…" : "➕ Crear admin"}
          </button>
        </div>

        {/* Promover a admin */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr auto",
            gap: 10,
            alignItems: "end",
          }}
        >
          <input
            className="form-input"
            placeholder="Email de usuario a promover"
            value={promoteEmail}
            onChange={(e) => setPromoteEmail(e.target.value)}
          />
          <button
            className="form-button"
            onClick={handlePromoteAdmin}
            disabled={busyPromote}
            title="Convierte un usuario existente en administrador"
          >
            {busyPromote ? "Promoviendo…" : "⬆️ Promover a admin"}
          </button>
        </div>
      </section>

      {/* Usuarios */}
      <section style={{ marginTop: 18 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <h3 style={{ margin: 0 }}>Usuarios ({users.length})</h3>
          <input
            className="form-input"
            placeholder="Filtrar por nombre o email…"
            value={qUser}
            onChange={(e) => setQUser(e.target.value)}
            style={{ maxWidth: 360 }}
          />
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: 14,
            marginTop: 12,
          }}
        >
          {filteredUsers.map((u) => (
            <div
              key={u.id}
              style={{
                border: "1px solid #e5eaf0",
                borderRadius: 12,
                padding: 14,
                background: "#fff",
                boxShadow: "0 2px 10px rgba(0,0,34,0.06)",
                display: "flex",
                flexDirection: "column",
                gap: 8,
              }}
            >
              <div style={{ fontWeight: 700, color: "#1e2a3a" }}>
                {u.name} {u.surname}
              </div>
              <div style={{ color: "#41546b", fontSize: ".95em" }}>{u.email}</div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <div style={{ fontSize: ".9em", color: u.is_admin ? "#2e7d32" : "#888" }}>
                  {u.is_admin ? "Administrador" : "Usuario"}
                </div>
                {u.is_blocked && (
                  <span
                    style={{
                      background: "#ffebee",
                      color: "#c62828",
                      padding: "2px 8px",
                      borderRadius: 999,
                      fontSize: ".8em",
                    }}
                  >
                    bloqueado
                  </span>
                )}
              </div>

              <div style={{ display: "flex", gap: 8, marginTop: 6, flexWrap: "wrap" }}>
                {!u.is_blocked ? (
                  <button className="form-button" onClick={() => handleBlockUser(u)}>
                    🔒 Bloquear
                  </button>
                ) : (
                  <button className="form-button" onClick={() => handleUnblockUser(u)}>
                    🔓 Desbloquear
                  </button>
                )}

                <button
                  className="form-button"
                  onClick={() => handleSetPasswordForUser(u)}
                  title="Cambiar contraseña de este usuario"
                >
                  🔑 Cambiar contraseña
                </button>

                <button
                  className="form-button"
                  style={{ background: "#f44336", color: "#fff" }}
                  onClick={() => handleDeleteUser(u)}
                >
                  🗑️ Borrar usuario
                </button>
              </div>
            </div>
          ))}
          {filteredUsers.length === 0 && (
            <div style={{ color: "#888" }}>No hay usuarios que coincidan con el filtro.</div>
          )}
        </div>
      </section>

      {/* Anuncios */}
      <section style={{ marginTop: 26 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <h3 style={{ margin: 0 }}>Anuncios ({ads.length})</h3>
          <input
            className="form-input"
            placeholder="Filtrar por título, descripción o email…"
            value={qAd}
            onChange={(e) => setQAd(e.target.value)}
            style={{ maxWidth: 360 }}
          />
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: 16,
            marginTop: 12,
          }}
        >
          {filteredAds.map((ad) => (
            <div
              key={ad.id}
              style={{
                border: "1px solid #e5eaf0",
                borderRadius: 12,
                padding: 14,
                background: "#fff",
                boxShadow: "0 2px 10px rgba(0,0,34,0.06)",
                display: "flex",
                flexDirection: "column",
                gap: 10,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 12,
                }}
              >
                <div style={{ fontWeight: 700, fontSize: "1.05rem", color: "#1e2a3a" }}>
                  {ad.title || `Anuncio #${ad.id}`}
                </div>
                <StatusBadge status={ad.status} />
              </div>

              <div style={{ color: "#41546b", fontSize: ".95em" }}>{ad.description}</div>
              <div style={{ fontSize: ".9em", color: "#667" }}>
                Publicado por: <b>{ad.user_email}</b>
              </div>

              {/* Imágenes */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {Array.isArray(ad.images) && ad.images.length > 0 ? (
                  ad.images.map((img, i) => {
                    const src = toImg(img);
                    const key = typeof img === "object" ? img.id ?? i : i;
                    return (
                      <div key={key} className="img-thumb">
                        <img
                          src={src}
                          alt=""
                          title={typeof img === "object" ? img.url : String(img)}
                          style={{
                            width: 84,
                            height: 84,
                            objectFit: "cover",
                            borderRadius: 8,
                            border: "1px solid #dfe6ee",
                            cursor: "zoom-in",
                          }}
                          onClick={() => setZoomSrc(src)}
                          onError={(e) => (e.currentTarget.style.opacity = 0.3)}
                        />
                        {typeof img === "object" && img.id && (
                          <button
                            type="button"
                            className="img-x"
                            title="Eliminar imagen"
                            aria-label="Eliminar imagen"
                            onClick={() => handleDeleteOneImage(ad.id, img)}
                          >
                            <Icon name="close" size={14} className="spin-on-hover" />
                          </button>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div
                    style={{
                      width: 110,
                      height: 66,
                      background: "#eef3f9",
                      color: "#98a6b8",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      borderRadius: 8,
                      fontSize: ".9em",
                    }}
                  >
                    Sin fotos
                  </div>
                )}
              </div>

              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {ad.status !== "active" ? (
                  <button className="form-button" onClick={() => handleUnblockAd(ad)}>
                    ✅ Marcar como activo
                  </button>
                ) : (
                  <button className="form-button" onClick={() => handleBlockAd(ad)}>
                    🚫 Poner en revisión
                  </button>
                )}

                <button
                  className="form-button"
                  style={{ background: "#f44336", color: "#fff" }}
                  onClick={() => handleDeleteAd(ad)}
                >
                  🗑️ Borrar anuncio
                </button>
              </div>
            </div>
          ))}
          {filteredAds.length === 0 && (
            <div style={{ color: "#888" }}>No hay anuncios que coincidan con el filtro.</div>
          )}
        </div>
      </section>

      {/* Modal zoom imagen */}
      {zoomSrc && (
        <div
          onClick={() => setZoomSrc(null)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,.75)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "zoom-out",
            zIndex: 5000,
          }}
        >
          <img
            src={zoomSrc}
            alt="zoom"
            style={{
              maxWidth: "92vw",
              maxHeight: "88vh",
              borderRadius: 12,
              background: "#fff",
              border: "2px solid #fff",
              boxShadow: "0 10px 30px rgba(0,0,0,.3)",
            }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
};

export default AdminPanel;
