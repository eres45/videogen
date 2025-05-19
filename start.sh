#!/bin/bash
set -e  # Exit immediately if a command fails

echo "====== Starting MoneyPrinterTurbo service ======"

# Set default values for environment variables
PORT=${PORT:-8080}
RENDER_EXTERNAL_URL=${RENDER_EXTERNAL_URL:-"http://localhost:$PORT"}

# Setup storage directories
mkdir -p storage/cache_videos
mkdir -p storage/tasks
chmod 755 storage/cache_videos storage/tasks

# Disk space management - clean up old files (older than 2 days)
echo "Cleaning up old video files..."
find storage/tasks -type f -mtime +2 -name "*.mp4" -delete
find storage/cache_videos -type f -mtime +3 -delete

# Copy the Render configuration template to config.toml
echo "Configuring application..."
cp config.render.toml config.toml

# Set default API keys if environment variables are not set
PEXELS_API_KEY=${PEXELS_API_KEY:-'wDEUJxQv8o9VV0gYat55LnXh0Sl9YlKBH5qZCOlDp03oEKGxJSXX23IH'}
PIXABAY_API_KEY=${PIXABAY_API_KEY:-'50386645-0aa0825cedfcdb43b883ce256'}
LLM_PROVIDER=${LLM_PROVIDER:-'pollinations'}
HIDE_CONFIG=${HIDE_CONFIG:-'true'}

# Replace environment variable placeholders with actual values
sed -i "s/\${PEXELS_API_KEY}/${PEXELS_API_KEY}/g" config.toml
sed -i "s/\${PIXABAY_API_KEY}/${PIXABAY_API_KEY}/g" config.toml
sed -i "s/\${OPENAI_API_KEY}/${OPENAI_API_KEY:-''}/g" config.toml
sed -i "s/\${POLLINATIONS_API_KEY}/${POLLINATIONS_API_KEY:-''}/g" config.toml
sed -i "s/\${POLLINATIONS_MODEL}/${POLLINATIONS_MODEL:-'openai-fast'}/g" config.toml
sed -i "s/\${LLM_PROVIDER}/${LLM_PROVIDER}/g" config.toml
sed -i "s/\${HIDE_CONFIG}/${HIDE_CONFIG}/g" config.toml
sed -i "s~\${RENDER_EXTERNAL_URL}~$RENDER_EXTERNAL_URL~g" config.toml
sed -i "s/\${PORT}/$PORT/g" config.toml

# Create health check endpoint
echo "Setting up health check endpoint..."
cat > app/health.py << EOF
from fastapi import APIRouter
import psutil
import platform
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "platform": platform.platform()
        }
    }
EOF

# Add health check route to main API
if ! grep -q "health" app/asgi.py; then
    sed -i '/from app.routers import.*/ a\from app import health' app/asgi.py
    sed -i '/app.include_router.*/ a\app.include_router(health.router)' app/asgi.py
fi

# Install additional monitoring dependencies
pip install --no-cache-dir psutil

# Print startup information
echo "Starting application on port: $PORT"
echo "External URL: $RENDER_EXTERNAL_URL"

# Start memory monitoring in background
echo "Starting memory monitor..."
python memory_monitor.py &

# Start the application
echo "Starting main application..."
python main.py
