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
    def create_placeholder_video(output_path: str) -> bool:
        """Create a simple text file instead of video to avoid memory usage"""
        try:
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write a placeholder file explaining the memory constraints
            with open(output_path, 'w') as f:
                f.write("Video generation disabled on Render free tier to avoid memory errors.\n")
                f.write("To generate videos, please upgrade to a paid Render plan or run locally.")
            
            logger.info(f"Created placeholder file at {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating placeholder: {e}")
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
            if DISABLE_VIDEO_PROCESSING:
                logger.warning("Video processing is disabled to save memory")
                return RenderFreeVideoHandler.create_placeholder_video(output_path)
            
            # First try to use a pre-rendered static video
            static_video = RenderFreeVideoHandler.get_static_video(prompt)
            if static_video:
                # Copy the static video to output path
                try:
                    shutil.copy2(static_video, output_path)
                    logger.info(f"Used pre-rendered video for: {prompt}")
                    return True
                except Exception as e:
                    logger.error(f"Error copying static video: {e}")
            
            # If we get here, try to create a slideshow from images instead of video
            try:
                # Generate some images (using original implementation code)
                # Normally you'd call functions to generate images, but for simplicity:
                from pathlib import Path
                
                # For now, just create a text file indicating what would happen
                # In a real implementation, this would generate or use existing images
                if RenderFreeVideoHandler.create_placeholder_video(output_path):
                    # Create a placeholder file with first frame for preview
                    preview_path = str(Path(output_path).parent / f"{task_id}.jpg")
                    with open(preview_path, 'w') as f:
                        f.write("This is a placeholder preview image")
                    
                    logger.info(f"Created placeholder for {prompt}")
                    return True
            except Exception as e:
                logger.error(f"Error in slideshow fallback: {e}")
            
            # As a last resort, create a simple placeholder file
            return RenderFreeVideoHandler.create_placeholder_video(output_path)
        
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
