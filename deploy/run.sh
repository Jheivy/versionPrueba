#!/bin/bash
# Arranca el hub. Uso: deploy/run.sh   (cert.pem/key.pem de mkcert en server/)
cd "$(dirname "$0")/../server" || exit 1
export SCAN2PRINT_PORT=8443
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8443 \
  --ssl-certfile cert.pem --ssl-keyfile key.pem
