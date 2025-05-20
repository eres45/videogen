"""
Render Free Plan Handler
This module implements an alternative approach to video generation that works 
within the extreme memory constraints of Render's free plan.
"""

import os
import sys
import json
import time
import base64
import requests
from loguru import logger
from typing import Dict, Any, List, Optional
import threading
import shutil

# Check if we're running on Render's free tier
IS_RENDER_FREE = os.environ.get("EXTREME_MEMORY_SAVING", "").lower() == "true"
DISABLE_VIDEO_PROCESSING = os.environ.get("DISABLE_VIDEO_PROCESSING", "").lower() == "true"

# Store original video generation function for fallback
original_video_generator = None

class RenderFreeVideoHandler:
    """
    Handler for generating videos on Render free tier by using:
    1. Static pre-rendered videos
    2. Simplified image slideshows instead of full videos
    3. Link to external video services rather than processing videos locally
    """
    
    @staticmethod
    def get_static_video(prompt: str, style: str = None) -> Optional[str]:
        """Return a path to a pre-rendered static video based on prompt similarity"""
        try:
            # Directory of pre-rendered videos
            static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "static_videos")
            
            # If directory doesn't exist, create it
            if not os.path.exists(static_dir):
                os.makedirs(static_dir, exist_ok=True)
                logger.info(f"Created static videos directory at {static_dir}")
                return None
                
            # Get list of available static videos
            videos = [f for f in os.listdir(static_dir) if f.endswith('.mp4')]
            
            if not videos:
                return None
                
            # For now just return a random video (in a real implementation, 
            # we would match based on prompt similarity)
            import random
            chosen_video = random.choice(videos)
            
            return os.path.join(static_dir, chosen_video)
        except Exception as e:
            logger.error(f"Error in get_static_video: {e}")
            return None
    
    @staticmethod
    def create_image_slideshow(images: List[str], output_path: str) -> bool:
        """
        Create a simple HTML file that displays images as a slideshow
        This uses much less memory than generating a video
        """
        try:
            # Create a simple HTML slideshow
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Video Generation</title>
                <style>
                    body { margin: 0; background: black; display: flex; justify-content: center; align-items: center; height: 100vh; }
                    .slideshow { max-width: 100%; max-height: 90vh; position: relative; }
                    .slide { display: none; width: 100%; }
                    img { max-width: 100%; max-height: 90vh; display: block; margin: 0 auto; }
                    .active { display: block; }
                    .controls { position: absolute; bottom: 20px; width: 100%; display: flex; justify-content: center; }
                    .controls button { background: rgba(255,255,255,0.5); border: none; padding: 10px 20px; margin: 0 5px; cursor: pointer; }
                </style>
            </head>
            <body>
                <div class="slideshow">
            """
            
            # Add images to the slideshow
            for i, img_path in enumerate(images):
                # Copy image to output directory if needed
                filename = os.path.basename(img_path)
                output_dir = os.path.dirname(output_path)
                target_path = os.path.join(output_dir, filename)
                
                # Copy the image if it's not already there
                if img_path != target_path:
                    shutil.copy2(img_path, target_path)
                
                # Add to slideshow
                active = " active" if i == 0 else ""
                html_content += f'<div class="slide{active}"><img src="{filename}" alt="Slide {i+1}"></div>\n'
            
            # Add controls and JavaScript
            html_content += """
                    <div class="controls">
                        <button id="prevBtn">Previous</button>
                        <button id="nextBtn">Next</button>
                        <button id="playBtn">Play</button>
                    </div>
                </div>
                <script>
                    let slideIndex = 0;
                    let slides = document.querySelectorAll('.slide');
                    let playing = false;
                    let slideInterval;
                    
                    function showSlide(n) {
                        // Hide all slides
                        for (let i = 0; i < slides.length; i++) {
                            slides[i].classList.remove('active');
                        }
                        
                        // Calculate the correct index
                        slideIndex = (n + slides.length) % slides.length;
                        
                        // Show the current slide
                        slides[slideIndex].classList.add('active');
                    }
                    
                    function nextSlide() {
                        showSlide(slideIndex + 1);
                    }
                    
                    function prevSlide() {
                        showSlide(slideIndex - 1);
                    }
                    
                    function togglePlay() {
                        if (playing) {
                            clearInterval(slideInterval);
                            document.getElementById('playBtn').textContent = 'Play';
                        } else {
                            slideInterval = setInterval(nextSlide, 2000);
                            document.getElementById('playBtn').textContent = 'Pause';
                        }
                        playing = !playing;
                    }
                    
                    // Add event listeners
                    document.getElementById('nextBtn').addEventListener('click', nextSlide);
                    document.getElementById('prevBtn').addEventListener('click', prevSlide);
                    document.getElementById('playBtn').addEventListener('click', togglePlay);
                    
                    // Start playing automatically
                    togglePlay();
                </script>
            </body>
            </html>
            """
            
            # Write to HTML file
            html_path = output_path.replace('.mp4', '.html')
            with open(html_path, 'w') as f:
                f.write(html_content)
            
            # Create a placeholder MP4 file with a text message
            with open(output_path, 'w') as f:
                f.write(f"This is a placeholder file. Please open the HTML slideshow at {html_path}")
            
            logger.info(f"Created image slideshow HTML at {html_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating slideshow: {e}")
            return False
    
    @staticmethod
    def create_minimal_video(output_path: str, prompt: str = "Video") -> bool:
        """Create a minimal video using extremely low memory techniques"""
        try:
            import subprocess
            import tempfile
            import shutil
            from pathlib import Path
            
            logger.info(f"Creating minimal video for prompt: {prompt}")
            
            # Create temp directory for our work
            with tempfile.TemporaryDirectory() as temp_dir:
                # Generate a single frame with text
                text_frame = os.path.join(temp_dir, "frame.txt")
                with open(text_frame, 'w') as f:
                    f.write(f"drawtext=text='{prompt}':x=(w-tw)/2:y=(h-th)/2:fontsize=24:fontcolor=white")
                
                # Create a tiny 10-second video with the specified prompt as text
                # Using the absolute minimum settings for ffmpeg
                cmd = [
                    "ffmpeg",
                    "-f", "lavfi",  # Use libavfilter virtual input
                    "-i", "color=c=black:s=320x240:d=5",  # Create a black background for 5 seconds
                    "-vf", f"drawtext=text='{prompt}':x=(w-tw)/2:y=(h-th)/2:fontsize=24:fontcolor=white",  # Add text
                    "-c:v", "libx264",  # Use x264 codec
                    "-preset", "ultrafast",  # Fastest encoding
                    "-tune", "fastdecode",  # Optimize for decoding speed
                    "-pix_fmt", "yuv420p",  # Standard pixel format
                    "-profile:v", "baseline",  # Most compatible profile
                    "-level", "3.0",
                    "-crf", "45",  # Very low quality
                    "-r", "1",  # 1 frame per second
                    "-t", "5",  # 5 second duration
                    "-movflags", "+faststart",  # Optimize for web playback
                    "-threads", "1",  # Use a single thread
                    output_path
                ]
                
                # Set extreme memory limit for ffmpeg subprocess
                # Create output directory if it doesn't exist
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Use subprocess with low memory
                env = os.environ.copy()
                env["MALLOC_ARENA_MAX"] = "1"
                
                # Run ffmpeg with minimal memory
                logger.info(f"Running minimal ffmpeg: {' '.join(cmd)}")
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    env=env
                )
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"ffmpeg failed: {stderr.decode('utf-8')}")
                    
                    # If ffmpeg fails, create a simple file
                    with open(output_path, 'w') as f:
                        f.write(f"Video for: {prompt}\nFailed to create due to memory constraints.")
                    
                    # Try to create at least a small MP4 file with one frame
                    try:
                        # Create a static image
                        preview_path = str(Path(output_path).with_suffix('.jpg'))
                        with open(preview_path, 'wb') as f:
                            # Create a small black JPG with text using bash
                            simple_cmd = [
                                "convert", "-size", "320x240", "xc:black", "-gravity", "center",
                                "-pointsize", "24", "-fill", "white", "-annotate", "0", prompt,
                                "jpg:-"
                            ]
                            img_process = subprocess.Popen(simple_cmd, stdout=f, stderr=subprocess.PIPE, env=env)
                            img_process.communicate()
                            
                            if img_process.returncode == 0:
                                logger.info(f"Created static preview image at {preview_path}")
                    except Exception as e:
                        logger.error(f"Failed to create preview image: {e}")
                    
                    return False
                else:
                    logger.info(f"Successfully created minimal video at {output_path}")
                    return True
        except Exception as e:
            logger.error(f"Error creating minimal video: {e}")
            
            # Fallback to a simple file
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w') as f:
                    f.write(f"Video for: {prompt}\nFailed to create due to memory constraints.")
                return False
            except:
                return False


def patch_video_generation():
    """
    Patch the video generation functions to use our free tier handler
    """
    if not IS_RENDER_FREE:
        logger.info("Not running on Render free tier, not applying video generation patches")
        return
        
    logger.warning("PATCHING VIDEO GENERATION FOR RENDER FREE TIER")
    
    # Import the video generation module
    try:
        from app.services.generation.video_generation import generate_video
        
        # Store original function for fallback
        global original_video_generator
        original_video_generator = generate_video
        
        # Create new function that implements our memory-saving approach
        def render_free_generate_video(prompt, task_id, output_path, **kwargs):
            """Replacement video generation function that works on Render free tier"""
            logger.info(f"Using Render free tier video generation for: {prompt}")
            
            # Check if video processing is completely disabled
            disable_processing = os.environ.get("DISABLE_VIDEO_PROCESSING", "").lower() == "true"
            
            # Always try to use a pre-rendered static video first
            static_video = RenderFreeVideoHandler.get_static_video(prompt)
            if static_video:
                # Copy the static video to output path
                try:
                    shutil.copy2(static_video, output_path)
                    logger.info(f"Used pre-rendered video for: {prompt}")
                    
                    # Create a preview image for the UI
                    from pathlib import Path
                    preview_path = str(Path(output_path).parent / f"{task_id}.jpg")
                    try:
                        # Extract first frame as preview using minimal memory
                        cmd = [
                            "ffmpeg", "-i", static_video,
                            "-vframes", "1", "-f", "image2",
                            "-loglevel", "error",
                            preview_path
                        ]
                        import subprocess
                        subprocess.run(cmd, capture_output=True)
                    except Exception:
                        # On failure, just create an empty preview file
                        with open(preview_path, 'w') as f:
                            f.write(f"Preview for {prompt}")
                    
                    return True
                except Exception as e:
                    logger.error(f"Error copying static video: {e}")
            
            # If we get here and video processing is disabled, create minimal fallback
            if disable_processing:
                logger.warning("Full video processing is disabled, creating minimal video")
                # Clean up the prompt for use in the video text
                safe_prompt = prompt.replace("'", "").replace("\"", "")[:50]  # Limit length
                return RenderFreeVideoHandler.create_minimal_video(output_path, safe_prompt)
            
            # Otherwise, try to generate an extremely minimal video
            try:
                logger.info(f"Generating minimal video for prompt: {prompt}")
                # Clean up the prompt for use in the video text
                safe_prompt = prompt.replace("'", "").replace("\"", "")[:50]  # Limit length
                
                # Create minimal video with text
                success = RenderFreeVideoHandler.create_minimal_video(output_path, safe_prompt)
                
                # Create a preview image
                from pathlib import Path
                preview_path = str(Path(output_path).parent / f"{task_id}.jpg")
                
                # Try to extract first frame for preview
                try:
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        cmd = [
                            "ffmpeg", "-i", output_path,
                            "-vframes", "1", "-f", "image2",
                            "-loglevel", "error",
                            preview_path
                        ]
                        import subprocess
                        subprocess.run(cmd, capture_output=True)
                except Exception as e:
                    logger.error(f"Failed to extract preview: {e}")
                    # Create fallback preview
                    with open(preview_path, 'w') as f:
                        f.write(f"Preview for {safe_prompt}")
                
                return success
            except Exception as e:
                logger.error(f"Error creating minimal video: {e}")
            
            # As a last resort, create a minimal text video
            logger.warning(f"Using last resort minimal video for {prompt}")
            safe_prompt = prompt.replace("'", "").replace("\"", "")[:30]  # Very short for stability
            return RenderFreeVideoHandler.create_minimal_video(output_path, safe_prompt)
        
        # Replace the original function with our version
        from app.services.generation import video_generation
        video_generation.generate_video = render_free_generate_video
        
        logger.warning("Successfully patched video generation for Render free tier")
        
    except ImportError as e:
        logger.error(f"Could not patch video generation: {e}")
    except Exception as e:
        logger.error(f"Error patching video generation: {e}")

# Apply patches when module is loaded
if IS_RENDER_FREE:
    logger.warning("Running on Render free tier with extreme memory optimizations")
    patch_video_generation()
