#!/bin/bash
set -e

echo "Running database migrations..."
cd api
alembic upgrade head
cd ..

echo "Starting FastAPI application..."
uvicorn api.src.main:app --host 0.0.0.0 --port ${PORT:-8000}