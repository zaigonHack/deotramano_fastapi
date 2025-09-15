# app/config.py

from dotenv import load_dotenv
import os
from pathlib import Path

# Cargar el archivo .env desde la raíz del proyecto
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Variables de entorno disponibles en todo el proyecto
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./deotramano.db")

