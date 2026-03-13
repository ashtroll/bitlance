#!/bin/bash
set -e

echo "Starting Bitlance platform..."

# Check for .env
if [ ! -f .env ]; then
  echo "ERROR: .env file not found. Copy .env.example and fill in values."
  exit 1
fi

# Build and start
docker compose up --build -d

echo ""
echo "Bitlance is running:"
echo "  Backend API: http://localhost:8000"
echo "  API Docs:    http://localhost:8000/docs"
echo "  Frontend:    http://localhost:3000"
