from .database import Base, engine
from .models import User

print("Creando base de datos...")
Base.metadata.create_all(bind=engine)
print("Base de datos creada correctamente.")
