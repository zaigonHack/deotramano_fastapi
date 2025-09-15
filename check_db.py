# check_db.py
import sqlite3

DB_PATH = "deotramano.db"   # ajusta si tu .env apunta a otra ruta

def check_password_history():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ¿existe la tabla?
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='password_history';")
    table = cur.fetchone()
    if not table:
        print("❌ La tabla 'password_history' NO existe en la base de datos.")
        return

    print("✅ La tabla 'password_history' existe.")

    # Mostrar columnas
    cur.execute("PRAGMA table_info(password_history);")
    cols = cur.fetchall()
    print("   Columnas:")
    for c in cols:
        print(f"   - {c[1]} ({c[2]})")

    # Mostrar algunas filas (si hay datos)
    cur.execute("SELECT id, user_id, created_at FROM password_history ORDER BY created_at DESC LIMIT 5;")
    rows = cur.fetchall()
    if rows:
        print("\nÚltimos registros:")
        for r in rows:
            print(r)
    else:
        print("\n(no hay registros todavía en password_history)")

    conn.close()

if __name__ == "__main__":
    check_password_history()
