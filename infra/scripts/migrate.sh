#!/bin/bash
set -e

echo "Running database migrations..."
cd backend
alembic upgrade head
echo "Migrations complete."
