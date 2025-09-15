#!/bin/bash

if [[ $1 == "prod" ]]; then
  cp app/main_prod.py app/main.py
  echo "¡Modo PRODUCCIÓN activado!"
elif [[ $1 == "dev" ]]; then
  cp app/main_dev.py app/main.py
  echo "¡Modo DESARROLLO activado!"
else
  echo "Uso: ./switch_mode.sh [prod|dev]"
  echo "Ejemplo: ./switch_mode.sh prod   # para producción"
  echo "         ./switch_mode.sh dev    # para desarrollo"
fi
