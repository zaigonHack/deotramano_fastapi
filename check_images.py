#!/usr/bin/env python3
# check_images.py
#
# Recorre una carpeta (por defecto: static/images) y muestra:
# - Tamaño WxH
# - Tamaño de archivo
# - Lado mayor
# - Estado (OK / > 2048px / error)
#
# Requiere: Pillow

from pathlib import Path
from PIL import Image, UnidentifiedImageError
import argparse
import os
import sys
from typing import Tuple

TARGET_MAX_SIDE = 2048
VALID_EXT = (".jpg", ".jpeg", ".png", ".webp")

def human_size(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

def get_dims(p: Path) -> Tuple[int, int]:
    with Image.open(p) as im:
        return im.size  # (w, h)

def main():
    parser = argparse.ArgumentParser(
        description="Audita imágenes y marca las que superan 2048 px en el lado mayor."
    )
    parser.add_argument(
        "--dir",
        default="static/images",
        help="Carpeta a escanear (por defecto: static/images)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Devuelve código de salida 1 si hay alguna imagen > 2048 px."
    )
    args = parser.parse_args()

    base = Path(args.dir)
    if not base.is_dir():
        print(f"✗ La carpeta no existe: {base}", file=sys.stderr)
        sys.exit(2)

    files = [p for p in base.iterdir() if p.is_file() and p.suffix.lower() in VALID_EXT]
    if not files:
        print(f"(Sin imágenes con extensión {VALID_EXT} en {base})")
        sys.exit(0)

    over = 0
    ok = 0
    err = 0

    # Encabezado
    print(f"Escaneando: {base.resolve()}")
    print("-" * 88)
    print(f"{'Archivo':40} {'WxH':>14} {'LadoMax':>8} {'Tamaño':>10}  Estado")
    print("-" * 88)

    for f in sorted(files, key=lambda x: x.name.lower()):
        try:
            size_bytes = f.stat().st_size
            w, h = get_dims(f)
            max_side = max(w, h)
            state = "OK" if max_side <= TARGET_MAX_SIDE else f"> {TARGET_MAX_SIDE}"
            if max_side <= TARGET_MAX_SIDE:
                ok += 1
            else:
                over += 1
            print(f"{f.name:40.40s} {f'{w}x{h}':>14} {max_side:>8} {human_size(size_bytes):>10}  {state}")
        except UnidentifiedImageError:
            err += 1
            print(f"{f.name:40.40s} {'-':>14} {'-':>8} {human_size(f.stat().st_size):>10}  ERROR: no es imagen válida")
        except Exception as e:
            err += 1
            print(f"{f.name:40.40s} {'-':>14} {'-':>8} {human_size(f.stat().st_size):>10}  ERROR: {e}")

    print("-" * 88)
    print(f"Resumen -> OK: {ok} | > {TARGET_MAX_SIDE}px: {over} | Errores: {err} | Total: {ok+over+err}")

    if args.strict and over > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
