#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Setup virtual environment
[ -d "venv" ] || python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

[ -f ".env" ] || echo "No .env file found. Please create one."

echo ""
echo "Starting Stats Microservice on port 3038..."
echo ""

uvicorn src.api:app --host 0.0.0.0 --port 3038 --reload
