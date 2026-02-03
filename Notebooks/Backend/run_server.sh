#!/usr/bin/env bash
# Run the FastAPI server from the project root. Use: ./run_server.sh

cd "$(dirname "$0")"

echo "Working directory: $(pwd)"
echo "Starting server on http://127.0.0.1:8000 ..."
echo "Docs: http://127.0.0.1:8000/docs"
echo ""

python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
