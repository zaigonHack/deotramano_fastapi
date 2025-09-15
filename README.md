DeOtraMano – Plataforma de anuncios con FastAPI + React
Este proyecto integra un backend en FastAPI con un frontend moderno en React (Vite), pensado para publicar, gestionar y visualizar anuncios de segunda mano.

📦 Estructura del proyecto
├── app/ # Backend FastAPI
│ ├── auth/ # Autenticación
│ ├── database/ # DB y modelos
│ ├── utils/ # Build y utilidades
│ └── main.py # Entrypoint FastAPI
├── frontend/ # Frontend React (Vite)
├── requirements.txt # Dependencias Python
├── nixpacks.toml # Config Railway
├── vite.config.js # Configuración Vite
└── ...

📖 Cómo preparar y arrancar el entorno FastAPI de DeOtraMano
Crear entorno virtual
python3 -m venv venv
Crea un entorno virtual llamado venv en la carpeta del proyecto.

Activar entorno virtual
source venv/bin/activate
En Windows sería: venv\Scripts\activate

Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
Instala todas las librerías necesarias desde el archivo requirements.txt.

Ejecutar el servidor
uvicorn app.main:app --reload
Levanta el servidor de FastAPI con autoreload para desarrollo.

Solución rápida si algo falla

¿No reconoce uvicorn o fastapi?

Revisa que el entorno virtual esté activado. Si no, actívalo (paso 2).

¿Dependencias rotas o faltantes?
Reinstala todo:
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Limpiar caché de Python (en casos extremos):
find . -type d -name "pycache" -exec rm -r {} +

Recomendaciones extra

Usa siempre el mismo entorno virtual para no mezclar librerías.

Cuando agregues nuevas librerías, actualiza el requirements.txt con:
pip freeze > requirements.txt

Usa un archivo .env para variables de configuración sensibles y usa python-dotenv para cargarlo.

🚀 Cómo subir el proyecto a GitHub
Inicializar repositorio git (si no tienes uno ya)
git init

Añadir todos los archivos al staging
git add .

Hacer commit con mensaje
git commit -m "Inicial commit proyecto DeOtraMano"

Crear un repositorio en GitHub (en web)

Añadir el repositorio remoto (cambia la URL por la tuya)
git remote add origin https://github.com/tu-usuario/tu-repositorio.git

Subir los cambios al repositorio remoto
git branch -M main
git push -u origin main

¡Listo! Ahora tu proyecto está versionado y alojado en GitHub.

entonces cual tengo que usar en desarrollo ./switch_mode.sh dev?


ChatGPT Plus
¡Exacto!
Si has creado el script switch_mode.sh (que te propuse antes), solo tienes que hacer:

bash

./switch_mode.sh dev
Esto hará lo siguiente:

Comenta el bloque de producción (que sirve el frontend desde FastAPI).

Descomenta el bloque de desarrollo (solo API).

Así puedes trabajar con React en el puerto 5173 y FastAPI solo como backend en 8000.

Luego, para producción, simplemente harías:

bash

./switch_mode.sh prod
Y entonces FastAPI servirá el frontend (después de hacer npm run build en React).

¿Cómo funciona el flujo día a día?
Desarrollo local:

Lanzar el backend con:

bash

uvicorn app.main:app --reload --port 8000
Lanzar el frontend con:

bash

npm run dev
Trabajar en http://localhost:5173

Antes de desplegar a producción:

Ejecutar:


npm run build
Esto crea la carpeta dist con el frontend compilado.

Ejecutar:



./switch_mode.sh prod
Lanzar FastAPI (ahora sirve el frontend en :8000).

Para desarrollar con React y FastAPI por separado:



./switch_mode.sh dev
uvicorn app.main:app --reload --port 8000
npm run dev
Para preparar el despliegue/producción:



npm run build
./switch_mode.sh prod
uvicorn app.main:app --host 0.0.0.0 --port 8000

./switch_mode.sh dev

Modo desarrollo (para programar, hot reload, Vite y FastAPI separados):

./switch_mode.sh dev

En una terminal: uvicorn app.main:app --reload

En otra terminal, en /frontend: npm run dev

Trabaja en localhost:5173

Modo producción (frontend compilado, servido por FastAPI):

./switch_mode.sh prod

uvicorn app.main:app --reload

Navega en localhost:8000

El backend compila y copia el frontend automáticamente (no tienes que usar Vite directamente).  

Nunca necesitas tener los dos abiertos para ver el resultado final:

Para desarrollo: 5173

Para resultado final: 8000 (el 5173 puede estar cerrado)

Resumen rápido:
¿Qué quiero?	¿Qué abro?	¿Comando?
Programar frontend	5173	npm run dev
Probar API backend	8000	uvicorn ...
Ver web final	8000	(solo backend levantado)
Compilar frontend	8000 (modo prod)	(el backend lo compila solo)

TIP: Cuando quieras “copiar lo de 5173 al 8000”, simplemente ejecutas ./switch_mode.sh prod y levantas el backend. El propio arranque del backend compilará el frontend y lo copiará al sitio correcto, ¡sin preocuparte de nada!