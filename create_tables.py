from app.database import engine
import app.models

# Crear las tablas en la base de datos
app.models.Base.metadata.create_all(bind=engine)
