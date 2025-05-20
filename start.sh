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

# Check if we're in extreme memory saving mode
if [ "${EXTREME_MEMORY_SAVING:-false}" = "true" ]; then
    echo "[RENDER FREE TIER] Starting in extreme memory saving mode"
    
    # Create static directory for video placeholders
    mkdir -p static_videos
    
    # Create wrapper for ffmpeg that doesn't actually process video
    echo "Creating static ffmpeg wrapper..."
    chmod +x static_ffmpeg_wrapper.sh
    
    # Replace ffmpeg with our dummy wrapper
    export PATH="$(pwd):$PATH"
    alias ffmpeg="$(pwd)/static_ffmpeg_wrapper.sh"
    
    # Set ultra-aggressive memory limits
    export MALLOC_ARENA_MAX=1
    export MALLOC_MMAP_THRESHOLD_=131072
    export MALLOC_TRIM_THRESHOLD_=131072
    export PYTHONMALLOC=malloc
    export PYTHONUNBUFFERED=1
    export OPENBLAS_NUM_THREADS=1
    export OMP_NUM_THREADS=1
    export MKL_NUM_THREADS=1
    export NUMEXPR_NUM_THREADS=1
    export DISABLE_VIDEO_PROCESSING=true
    
    # Disable imagemagick
    export MAGICK_CONFIGURE_PATH=/dev/null
    
    # Ensure low memory Python settings
    export PYTHONHASHSEED=0
    
    # Hard memory limit
    ulimit -v 536870912  # 512MB virtual memory limit
    
    echo "Starting in PLACEHOLDER MODE - no actual video processing will occur"
    echo "This is required due to memory constraints on the free tier"
    
    # Start application with minimal features
    python -u main.py
else
    # Apply regular memory optimizations for Render
    echo "Applying memory optimizations for Render..."
    python render_memory_fix.py &

    # Start the application with reduced memory settings
    echo "Starting main application in memory-efficient mode..."
    export PYTHONMALLOC=malloc
    export MALLOC_TRIM_THRESHOLD_=65536
    export PYTHONUNBUFFERED=1
    export OPENBLAS_NUM_THREADS=1
    export OMP_NUM_THREADS=1
    python -u main.py
fi
