#!/bin/bash
# Stop containers and drop the MongoDB database defined in the env file
set -e


cd "$(dirname "$0")"

echo "WARNING: This script will STOP all containers and PERMANENTLY DELETE the MongoDB database configured in your .env file!"
read -p "Are you sure you want to continue? Type YES to proceed, or anything else to exit: " confirm
if [ "$confirm" != "YES" ]; then
  echo "Aborted. No changes made."
  exit 0
fi

docker compose down

echo "Containers stopped and removed."

# Load MongoDB connection info from env file (assumes .env in parent dir)
ENV_FILE="../.env"
if [ ! -f "$ENV_FILE" ]; then
  echo ".env file not found at $ENV_FILE. Aborting DB drop."
  exit 1
fi

MONGODB_URL=$(grep '^MONGODB_URL=' "$ENV_FILE" | cut -d '=' -f2-)
DATABASE_NAME=$(grep '^DATABASE_NAME=' "$ENV_FILE" | cut -d '=' -f2-)

if [ -z "$MONGODB_URL" ] || [ -z "$DATABASE_NAME" ]; then
  echo "MONGODB_URL or DATABASE_NAME not set in $ENV_FILE. Aborting DB drop."
  exit 1
fi

echo "Dropping MongoDB database: $DATABASE_NAME"
# Use Docker to run a MongoDB client and drop the database
# This assumes the MongoDB server is accessible from the network defined in docker-compose

docker run --rm mongo:7.0 mongo "$MONGODB_URL" --eval "db.getSiblingDB('$DATABASE_NAME').dropDatabase()"

echo "Database $DATABASE_NAME dropped."
