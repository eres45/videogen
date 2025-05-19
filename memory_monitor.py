#!/usr/bin/env python3
"""
Memory monitoring script to prevent out-of-memory errors on Render.
This script runs in the background and monitors memory usage,
cleaning up resources when memory usage gets too high.
"""

import os
import time
import signal
import psutil
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("MemoryMonitor")

# Settings
MEMORY_THRESHOLD = 80  # percentage
CLEAN_INTERVAL = 300  # seconds (5 minutes)
STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage")

def get_memory_usage():
    """Get current memory usage as percentage."""
    return psutil.virtual_memory().percent

def cleanup_old_videos():
    """Clean up old video files to free up memory."""
    try:
        tasks_dir = os.path.join(STORAGE_DIR, "tasks")
        cache_dir = os.path.join(STORAGE_DIR, "cache_videos")
        
        if not os.path.exists(tasks_dir) or not os.path.exists(cache_dir):
            logger.warning(f"Storage directories not found: {tasks_dir} or {cache_dir}")
            return
        
        # Delete video files older than 1 day in tasks directory
        cutoff_time = datetime.now() - timedelta(days=1)
        files_removed = 0
        
        # Clean tasks directory
        for root, dirs, files in os.walk(tasks_dir):
            for file in files:
                if file.endswith(".mp4"):
                    file_path = os.path.join(root, file)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_time:
                        try:
                            os.remove(file_path)
                            files_removed += 1
                        except Exception as e:
                            logger.error(f"Error removing file {file_path}: {str(e)}")
        
        # Clean cache directory
        for root, dirs, files in os.walk(cache_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_time:
                    try:
                        os.remove(file_path)
                        files_removed += 1
                    except Exception as e:
                        logger.error(f"Error removing file {file_path}: {str(e)}")
        
        logger.info(f"Memory cleanup: removed {files_removed} old video files")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

def main():
    """Main monitoring loop."""
    logger.info("Starting memory monitor...")
    
    try:
        while True:
            memory_usage = get_memory_usage()
            logger.info(f"Current memory usage: {memory_usage}%")
            
            if memory_usage > MEMORY_THRESHOLD:
                logger.warning(f"Memory usage high ({memory_usage}%), performing cleanup")
                cleanup_old_videos()
            
            time.sleep(CLEAN_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Memory monitor stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error in memory monitor: {str(e)}")

if __name__ == "__main__":
    main()
