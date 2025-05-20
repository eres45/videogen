import uvicorn
import os
import sys
import gc
from loguru import logger

from app.config import config

# Apply memory optimizations for Render free tier
def apply_render_memory_optimizations():
    logger.info("Applying Render free tier memory optimizations")
    
    # Check if we're running on Render's free tier with extreme memory saving mode
    is_render_free = os.environ.get("EXTREME_MEMORY_SAVING", "").lower() == "true"
    if is_render_free:
        logger.warning("EXTREME MEMORY SAVING MODE ENABLED - DISABLING VIDEO PROCESSING")
        
    # Reduce memory footprint
    os.environ["PYTHONMALLOC"] = "malloc"
    os.environ["MALLOC_TRIM_THRESHOLD_"] = "65536"
    
    # Limit thread usage
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"
    
    # If in extreme mode, completely disable video processing and use placeholders
    if is_render_free:
        try:
            # Import and apply our render free handler
            from app.services.render_free_handler import patch_video_generation
            patch_video_generation()
            logger.warning("Replaced video generation with free tier compatible version")
        except Exception as e:
            logger.error(f"Failed to patch video generation for free tier: {e}")
    else:
        # Apply regular video memory optimizations
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
        
        # If in extreme memory saving mode, set even more aggressive limits
        if is_render_free:
            config.app["max_concurrent_tasks"] = 1
            config.app["disable_video_processing"] = True
            
            # Modify video related functions to be no-ops
            logger.warning("Setting minimal video parameters for free tier")
        
        # Add ffmpeg params if they don't exist
        if "ffmpeg_params" not in config.app:
            config.app["ffmpeg_params"] = {}
            
        # Set low memory ffmpeg parameters
        config.app["ffmpeg_params"].update({
            "threads": "1",
            "preset": "ultrafast",
            "crf": "40",  # Extremely low quality to minimize memory
            "vf": "scale=320:-2",  # Dramatically reduced resolution
            "fs": "5M"  # Limit file size to 5MB
        })
        
        logger.info(f"Configured app for low memory: {config.app['ffmpeg_params']}")
    
    # Apply system-level optimizations
    if is_render_free:
        # Disable any unnecessary services
        try:
            import resource
            # Set maximum memory that can be allocated
            # 512MB in bytes (conservative for free tier)
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, -1))
            logger.warning("Set hard memory limit to 512MB")
        except Exception as e:
            logger.error(f"Failed to set memory limit: {e}")
    
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
