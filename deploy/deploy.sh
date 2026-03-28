#!/bin/bash
# Deploy script for Vcard API
set -e

cd "$(dirname "$0")"

echo "Building and starting containers..."
docker-compose up -d --build

echo "Deployment complete."
