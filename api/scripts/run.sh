#!/bin/sh

# Define the application base directory
APP_DIR="/app/api"

# Wait for dependent services to be ready (if necessary)
sleep 5

# Automatically load the .env file if found
set -a
if [ -e "$APP_DIR/.env" ]; then
    . "$APP_DIR/.env"
else
    echo "No .env file found. Exiting."
    exit 1
fi
set +a

# Navigate to the application directory
cd "$APP_DIR" || { echo "Failed to change directory to $APP_DIR. Exiting."; exit 1; }

# Check if SH_STATIC_DIR is empty and default it to 'static' if it is
if [ -z "$SH_STATIC_DIR" ]; then
    SH_STATIC_DIR="static"
fi

echo "SH_STATIC_DIR is set to: $SH_STATIC_DIR"

# Check and create SH_STATIC_DIR if necessary
if [ ! -d "$SH_STATIC_DIR" ]; then
    echo "Creating directory $SH_STATIC_DIR..."
    mkdir -p "$SH_STATIC_DIR" || { echo "Failed to create directory $SH_STATIC_DIR. Exiting."; exit 1; }
else
    echo "Directory $SH_STATIC_DIR already exists."
fi

# Database migration
if grep -qi '^RUN_MIGRATIONS=True' .env; then
    echo "Running Alembic migrations..."
    alembic upgrade head || { echo "Alembic upgrade failed. Exiting."; exit 1; }
fi

# Set the default message format for app mode
APP_MODE_MESSAGE="Starting the application in %s mode..."

# Default port if not set
PORT=${APP_PORT:-8080}

# Check the MODE environment variable
if [ "$MODE" = "PROD" ]; then
    # Production mode: start Supervisor
    echo "Starting the application in production mode..."
    /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf

elif [ "$MODE" = "DEV" ]; then
    # Development or debug mode
    if grep -qi '^DEBUG=True' .env; then
        printf "$APP_MODE_MESSAGE" "debug"
        # Start FastAPI application with Uvicorn in development mode
        uvicorn src.main:app \
            --host 0.0.0.0 \
            --port "$PORT" \
            --reload \
            --proxy-headers \
            --forwarded-allow-ips="*"
    else
        printf "$APP_MODE_MESSAGE" "production"
        # Start FastAPI application with Gunicorn + Uvicorn workers
        gunicorn src.main:app \
            --workers 4 \
            --worker-class uvicorn.workers.UvicornWorker \
            --bind "0.0.0.0:$PORT" \
            --proxy-headers \
            --forwarded-allow-ips="*"
    fi
else
    echo "No valid MODE set. Exiting..."
    exit 1
fi
