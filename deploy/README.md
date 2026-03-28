# Vcard API Deployment

## Structure
- `Dockerfile`: FastAPI app container
- `docker-compose.yml`: Orchestrates API, MongoDB, and Nginx
- `nginx/nginx.conf`: Nginx reverse proxy and static file serving
- `deploy.sh`: Build and start all services
- `down.sh`: Stop and remove all services

## Usage

1. **Set up your `.env` file** in the project root with all required environment variables (see `config.py`).
2. **Build and start services:**
   ```sh
   cd deploy
   ./deploy.sh
   ```
3. **Stop services:**
   ```sh
   ./down.sh
   ```

- Nginx will listen on port 80 and proxy `/api/` to the FastAPI app, serving static files from `/templates/`, `/thumbnails/`, and `/qrcodes/`.
- MongoDB data is persisted in a Docker volume.

## Notes
- Make sure your domain (e.g., `vcardapi.shoverhub.com`) points to your server's IP.
- Adjust `nginx.conf` and environment variables as needed for production.
