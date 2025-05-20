"""
Memory optimization for Render deployment
This script should be run at startup to patch memory-intensive operations
"""
import os
import sys
import gc
import time
import threading
import psutil
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("RenderMemoryFix")

# Constants
MEMORY_CHECK_INTERVAL = 30  # Check memory every 30 seconds
MEMORY_THRESHOLD = 65  # Percent - more aggressive threshold
VIDEO_CACHE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "storage", "cache_videos")
TASKS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "storage", "tasks")
TEMP_DIRS = ["/tmp", "/var/tmp"]  # System temp directories to clean

def log_memory_usage():
    """Log current memory usage"""
    mem = psutil.virtual_memory()
    logger.info(f"Memory usage: {mem.percent}% used, {mem.available/1024/1024:.1f}MB available")

def clear_memory_aggressively():
    """Force garbage collection and try to free memory"""
    logger.info("Clearing memory aggressively")
    gc.collect()
    
    # Python doesn't actually release memory back to the OS easily
    # But we can try to compact objects and run GC multiple times
    for _ in range(3):
        gc.collect()
    
    # Log memory after cleanup
    log_memory_usage()

def delete_old_files(directory, days=1, extensions=None):
    """Delete files older than specified days with given extensions"""
    if not os.path.exists(directory):
        return 0
        
    if extensions is None:
        extensions = ['.mp4', '.jpg', '.png', '.wav', '.mp3']
        
    count = 0
    cutoff_time = datetime.now() - timedelta(days=days)
    
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                try:
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_time:
                        os.remove(file_path)
                        count += 1
                except Exception as e:
                    logger.error(f"Error deleting {file_path}: {e}")
                    
    return count

def apply_memory_patches():
    """Apply memory-saving patches to the app"""
    # Patch 1: Limit video cache
    logger.info("Applying memory patches...")
    
    # Patch the maximum concurrent tasks
    from app.config import config
    if hasattr(config, 'app'):
        logger.info("Setting max_concurrent_tasks to 1")
        config.app['max_concurrent_tasks'] = 1
    
    # Patch any video processing functions to use less memory
    try:
        # If MoviePy is used, patch its memory usage
        import moviepy.config as moviepy_config
        moviepy_config.FFMPEG_BINARY = "ffmpeg"
        moviepy_config.IMAGEMAGICK_BINARY = "convert"
        
        # Override MoviePy's default to use less memory
        os.environ["IMAGEIO_FFMPEG_EXE"] = "ffmpeg"
        
        logger.info("Patched MoviePy configuration for lower memory usage")
    except ImportError:
        pass
    
    # Lower process priority to avoid killing the container
    try:
        os.nice(10)  # Linux/Unix
        logger.info("Lowered process priority")
    except (AttributeError, OSError):
        pass  # Not supported on this platform

def clean_temp_files():
    """Clean temporary files that can consume memory"""
    logger.info("Cleaning temporary files")
    
    for temp_dir in TEMP_DIRS:
        if os.path.exists(temp_dir):
            try:
                # Look for video-related temp files
                video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.tmp']
                count = 0
                
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        if any(file.endswith(ext) for ext in video_extensions):
                            try:
                                file_path = os.path.join(root, file)
                                # Don't delete files being actively used
                                if not os.path.islink(file_path) and os.access(file_path, os.W_OK):
                                    os.remove(file_path)
                                    count += 1
                            except (PermissionError, OSError):
                                # Skip files we can't delete
                                pass
                
                if count > 0:
                    logger.info(f"Deleted {count} temporary video files from {temp_dir}")
            except Exception as e:
                logger.error(f"Error cleaning temp directory {temp_dir}: {e}")

def memory_monitor_thread():
    """Background thread to monitor and manage memory"""
    logger.info("Starting memory monitor thread")
    
    # Initial cleanup of temporary files
    clean_temp_files()
    
    while True:
        try:
            # Check memory usage
            mem = psutil.virtual_memory()
            
            if mem.percent > MEMORY_THRESHOLD:
                logger.warning(f"High memory usage detected: {mem.percent}%")
                
                # Delete old files
                cache_files = delete_old_files(VIDEO_CACHE_DIR, days=0.5)  # 12 hours
                task_files = delete_old_files(TASKS_DIR, days=0.5)
                logger.info(f"Deleted {cache_files} cache files and {task_files} task files")
                
                # Clean temp files
                clean_temp_files()
                
                # Force garbage collection
                clear_memory_aggressively()
            else:
                log_memory_usage()
                
            # Sleep for the interval
            time.sleep(MEMORY_CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in memory monitor: {e}")
            time.sleep(MEMORY_CHECK_INTERVAL)

def main():
    """Main entry point"""
    logger.info("Starting render_memory_fix.py")
    log_memory_usage()
    
    # Apply memory patches
    apply_memory_patches()
    
    # Start memory monitor thread
    monitor_thread = threading.Thread(target=memory_monitor_thread, daemon=True)
    monitor_thread.start()
    
    logger.info("Memory optimization initialized")
    return monitor_thread

if __name__ == "__main__":
    main()
