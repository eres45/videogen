#!/bin/bash
set -e  # Exit immediately if a command fails

echo "====== Starting build process ======"

# Install system dependencies with minimal output and no prompts
echo "Installing system dependencies..."
apt-get update -qq
apt-get install -y --no-install-recommends imagemagick ffmpeg -qq

# Fix security policy for ImageMagick to allow more operations
echo "Configuring ImageMagick..."
if [ -f /etc/ImageMagick-6/policy.xml ]; then
    # Remove path restriction
    sed -i '/<policy domain="path" rights="none" pattern="@\*"/d' /etc/ImageMagick-6/policy.xml
    # Allow more memory usage for large video frames
    sed -i 's/<policy domain="resource" name="memory" value="[0-9]*"\/>/<!\-- <policy domain="resource" name="memory" value="256MiB"\/> -->/g' /etc/ImageMagick-6/policy.xml
    sed -i 's/<policy domain="resource" name="disk" value="[0-9]*"\/>/<!\-- <policy domain="resource" name="disk" value="1GiB"\/> -->/g' /etc/ImageMagick-6/policy.xml
fi

# Clean up apt cache to save disk space
apt-get clean
rm -rf /var/lib/apt/lists/*

# Install Python dependencies with progress bar
echo "Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

# Create config file if it doesn't exist
echo "Setting up configuration..."
if [ ! -f config.toml ]; then
    cp config.example.toml config.toml
fi

# Create storage directories
echo "Creating storage directories..."
mkdir -p storage/cache_videos
mkdir -p storage/tasks

echo "====== Build completed successfully ======"
