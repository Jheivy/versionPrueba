#!/bin/bash
# Muestra un QR y un código (10 min, un solo uso) para emparejar un móvil con este Mac.
#   deploy/pair.sh                       -> empareja un móvil
#   deploy/pair.sh token "mi agente"     -> token Bearer para un agente/script
#   deploy/pair.sh list | revoke <id>    -> ver / revocar dispositivos
cd "$(dirname "$0")/../server" || exit 1
exec .venv/bin/python -m app.auth "${@:-pair}"
