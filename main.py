import uvicorn
import os
import sys
import gc
from loguru import logger

from app.config import config

# Apply memory optimizations for Render free tier
def apply_render_memory_optimizations():
    logger.info("Applying Render free tier memory optimizations")
    
    # Reduce memory footprint
    os.environ["PYTHONMALLOC"] = "malloc"
    os.environ["MALLOC_TRIM_THRESHOLD_"] = "65536"
    
    # Limit thread usage
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"
    
    # Apply video memory optimizations
    try:
        from app.services.video_memory_patch import apply_patches
        apply_patches()
        logger.info("Applied video memory optimizations")
    except Exception as e:
        logger.error(f"Failed to apply video memory patches: {e}")
    
    # Force Python garbage collection
    gc.collect()
    
    # Set lower video quality in configuration
    if hasattr(config, 'app'):
        # Force extremely low video quality settings for free tier
        config.app["max_concurrent_tasks"] = 1
        config.app["low_memory_mode"] = True
        
        # Add ffmpeg params if they don't exist
        if "ffmpeg_params" not in config.app:
            config.app["ffmpeg_params"] = {}
            
        # Set low memory ffmpeg parameters
        config.app["ffmpeg_params"].update({
            "threads": "1",
            "preset": "ultrafast",
            "crf": "35",  # Very low quality but low memory
            "vf": "scale=480:-2",  # Reduce resolution dramatically
            "fs": "10M"  # Limit file size to 10MB
        })
        
        logger.info(f"Configured app for low memory: {config.app['ffmpeg_params']}")
    
    logger.info("Memory optimizations complete")
    return True

if __name__ == "__main__":
    # Apply memory optimizations first
    apply_render_memory_optimizations()
    
    logger.info(
        "Starting server in memory-optimized mode, docs: http://127.0.0.1:" + str(config.listen_port) + "/docs"
    )
    
    # Run with optimized settings
    uvicorn.run(
        app="app.asgi:app",
        host=config.listen_host,
        port=config.listen_port,
        reload=False,  # Disable reload to save memory
        log_level="warning",
        workers=1,  # Use single worker
        limit_concurrency=5,  # Limit concurrent connections
        timeout_keep_alive=30  # Shorter keep-alive timeout
    )
