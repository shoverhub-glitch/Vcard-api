#!/bin/bash
# Deploy script for Vcard API
set -e

cd "$(dirname "$0")"

echo "Building and starting containers..."
docker-compose up -d --build

echo "Deployment complete."

# Auto-create admin user if not exists
DEFAULT_ADMIN_EMAIL="rakeshalgot02@gmail.com"
DEFAULT_ADMIN_PASSWORD="Chittigadu@0406"

ADMIN_EMAIL="${ADMIN_EMAIL:-$DEFAULT_ADMIN_EMAIL}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-$DEFAULT_ADMIN_PASSWORD}"

echo "Ensuring admin user exists..."
docker-compose exec -T api python create_admin.py create --email "$ADMIN_EMAIL" --password "$ADMIN_PASSWORD" || true
