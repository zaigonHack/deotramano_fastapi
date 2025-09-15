import os
from sqlalchemy import create_engine
from app.database import Base
from app import models

DB_FILE = "deotramano.db"

# Borrar base de datos vieja si existe
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
    print(f"Base de datos {DB_FILE} eliminada.")

# Crear motor y tablas nuevas
engine = create_engine(f"sqlite:///{DB_FILE}")

Base.metadata.create_all(bind=engine)

print("Base de datos creada con tablas actualizadas.")
