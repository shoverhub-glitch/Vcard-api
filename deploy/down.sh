#!/bin/bash
# Stop and remove containers
set -e

cd "$(dirname "$0")"

docker-compose down

echo "Containers stopped and removed."
