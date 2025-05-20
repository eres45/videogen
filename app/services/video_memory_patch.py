"""
Video memory optimization patch for Render free tier
This is a monkey-patch module that replaces high-memory functions with optimized versions
"""

import os
import sys
import logging
from loguru import logger

# Try to import and patch MoviePy
try:
    import moviepy
    import moviepy.config
    import moviepy.video.io.ffmpeg_reader as ffmpeg_reader
    import moviepy.video.io.ffmpeg_writer as ffmpeg_writer
    from moviepy.video.io.ffmpeg_reader import ffmpeg_parse_infos
    import subprocess
    import tempfile
    
    # Store original functions
    original_parse_infos = ffmpeg_parse_infos
    original_ffmpeg_reader_init = ffmpeg_reader.FFMPEG_VideoReader.__init__
    
    # Configure MoviePy for low memory
    moviepy.config.FFMPEG_BINARY = "ffmpeg"  # Will be replaced with our wrapper if available
    
    # Create wrapper script if it doesn't exist
    def create_ffmpeg_wrapper():
        """Create a low-memory ffmpeg wrapper script"""
        wrapper_path = "/tmp/ffmpeg_low_mem"
        
        # Check if wrapper already exists
        if os.path.exists(wrapper_path):
            return wrapper_path
            
        # Create wrapper script content
        script = """#!/bin/bash
set -e

# Get all arguments
ARGS=("$@")

# Add memory-limiting arguments
EXTRA_ARGS=(
  "-threads" "1"
  "-preset" "ultrafast"
  "-crf" "35"
  "-loglevel" "error"
)

# Execute real ffmpeg with memory constraints
exec nice -n 19 ffmpeg ${EXTRA_ARGS[@]} "${ARGS[@]}"
"""
        
        # Write script to file
        try:
            with open(wrapper_path, 'w') as f:
                f.write(script)
            os.chmod(wrapper_path, 0o755)
            logger.info(f"Created low-memory ffmpeg wrapper at {wrapper_path}")
            return wrapper_path
        except Exception as e:
            logger.error(f"Failed to create ffmpeg wrapper: {e}")
            return "ffmpeg"  # Fallback to regular ffmpeg
    
    # Create the wrapper and set it
    ffmpeg_wrapper = create_ffmpeg_wrapper()
    moviepy.config.FFMPEG_BINARY = ffmpeg_wrapper
    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_wrapper
    
    # Patch the ffmpeg parse infos function to use lower resolution
    def patched_parse_infos(filename, print_infos=False, check_duration=True, fps_source='tbr'):
        """Patched version of ffmpeg_parse_infos that uses less memory"""
        logger.info(f"Using memory-optimized ffmpeg_parse_infos for {filename}")
        return original_parse_infos(filename, print_infos, False, fps_source)  # Skip duration check
    
    # Patch the FFMPEG_VideoReader init to use lower resolution buffers
    def patched_ffmpeg_reader_init(self, filename, bufsize=None, pix_fmt="rgb24", check_duration=False, 
                                 target_resolution=None, resize_algo="bicubic", fps_source='tbr'):
        """Patched version of FFMPEG_VideoReader.__init__ that uses less memory"""
        # Force smaller buffer size and lower resolution
        if bufsize is None or bufsize > 2**20:  # More than 1MB
            bufsize = 2**19  # Use 512KB buffer instead
            
        # Force resolution reduction if not already set
        if target_resolution is None:
            # Determine a smaller resolution based on input file
            try:
                # Get original dimensions using ffprobe
                cmd = [moviepy.config.FFMPEG_BINARY, "-i", filename, "-v", "error", 
                      "-select_streams", "v:0", "-show_entries", "stream=width,height", 
                      "-of", "csv=p=0"]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, _ = proc.communicate()
                output = output.decode('utf8').strip().split(',')
                
                if len(output) == 2:
                    width, height = map(int, output)
                    # Reduce to 480p maximum
                    if width > 480 or height > 480:
                        if width > height:
                            target_resolution = (480, -1)  # Auto-calculate height
                        else:
                            target_resolution = (-1, 480)  # Auto-calculate width
                            
                        logger.info(f"Reducing video resolution to {target_resolution}")
            except Exception as e:
                logger.error(f"Error determining video dimensions: {e}")
                # Default fallback - force lower resolution
                target_resolution = (480, -1)
        
        # Call original init with modified parameters
        logger.info(f"Initializing video reader with reduced memory settings: buf={bufsize}, res={target_resolution}")
        return original_ffmpeg_reader_init(self, filename, bufsize=bufsize, pix_fmt=pix_fmt, 
                                        check_duration=check_duration, target_resolution=target_resolution,
                                        resize_algo=resize_algo, fps_source=fps_source)
    
    # Replace the original functions with our patched versions
    ffmpeg_reader.ffmpeg_parse_infos = patched_parse_infos
    ffmpeg_reader.FFMPEG_VideoReader.__init__ = patched_ffmpeg_reader_init
    
    logger.info("Successfully patched MoviePy for lower memory usage")
    
except ImportError as e:
    logger.warning(f"MoviePy not found, skipping video memory optimizations: {e}")
except Exception as e:
    logger.error(f"Error patching MoviePy: {e}")

def apply_patches():
    """Apply additional memory patches"""
    logger.info("Applying additional video memory patches")
    
    # Limit concurrent video processing
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"
    
    # Set lower quality ffmpeg defaults
    os.environ["FFMPEG_PRESET"] = "ultrafast"
    os.environ["FFMPEG_CRF"] = "35"
    
    return True
