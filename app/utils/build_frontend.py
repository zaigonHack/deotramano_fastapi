# app/utils/build_frontend.py

import os
import shutil
import subprocess

def build_and_copy_frontend():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    frontend_src = os.path.join(root_dir, "frontend")
    frontend_dist = os.path.join(frontend_src, "dist")
    frontend_target = os.path.join(root_dir, "app", "frontend")

    if not os.path.exists(frontend_src):
        print("[❌] No se encontró la carpeta 'frontend'. ¿Está en el lugar correcto?")
        return

    print("[🔧] Compilando frontend con Vite...")

    try:
        subprocess.run(["npm", "install"], cwd=frontend_src, check=True)
        subprocess.run(["npm", "run", "build"], cwd=frontend_src, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[❌] Error durante la compilación del frontend: {e}")
        return

    if not os.path.exists(frontend_dist):
        print("[❌] La carpeta 'dist/' no fue generada. Algo falló en el build.")
        return

    # Limpiar destino
    if os.path.exists(frontend_target):
        shutil.rmtree(frontend_target)
    os.makedirs(frontend_target, exist_ok=True)

    # Copiar archivos compilados
    for item in os.listdir(frontend_dist):
        src = os.path.join(frontend_dist, item)
        dst = os.path.join(frontend_target, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    print("[✅] Frontend compilado y copiado exitosamente a app/frontend.")
