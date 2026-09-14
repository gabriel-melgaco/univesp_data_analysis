#!/usr/bin/env bash
# Sobe o dashboard (Streamlit) e a página (Django) juntos.
set -e
cd "$(dirname "$0")"

trap 'kill 0' EXIT

.venv/bin/streamlit run dashboard.py --server.headless true &
.venv/bin/python manage.py runserver 0.0.0.0:8001 &

echo "Página: http://localhost:8001 (rede: http://$(hostname -I | awk '{print $1}'):8001)"
echo "Streamlit direto: http://localhost:8501"
wait
