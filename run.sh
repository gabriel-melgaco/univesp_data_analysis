#!/usr/bin/env bash
# Sobe o dashboard (Streamlit) e a página (Django) juntos.
set -e
cd "$(dirname "$0")"

trap 'kill 0' EXIT

.venv/bin/streamlit run dashboard.py --server.headless true &
.venv/bin/python manage.py runserver 8001 &

echo "Dashboard: http://localhost:8001 (Streamlit direto: http://localhost:8501)"
wait
