#!/bin/bash
set -e  # Exit immediately if a command fails

echo "====== Starting build process ======"

# Install system dependencies with minimal output and no prompts
echo "Installing system dependencies..."
apt-get update -qq
apt-get install -y --no-install-recommends imagemagick ffmpeg python3-psutil -qq

# Configure ImageMagick with strict memory limits for Render environment
echo "Configuring ImageMagick with memory limitations..."
if [ -f /etc/ImageMagick-6/policy.xml ]; then
    # Remove path restriction
    sed -i '/<policy domain="path" rights="none" pattern="@\*"/d' /etc/ImageMagick-6/policy.xml
    
    # Set strict memory limits to prevent OOM
    sed -i 's/<policy domain="resource" name="memory" value="[0-9]*MiB"\/>/\<policy domain="resource" name="memory" value="128MiB"\/>\<policy domain="resource" name="map" value="64MiB"\/>/' /etc/ImageMagick-6/policy.xml
    sed -i 's/<policy domain="resource" name="disk" value="[0-9]*"\/>/\<policy domain="resource" name="disk" value="512MiB"\/>/' /etc/ImageMagick-6/policy.xml
    echo "<policy domain=\"resource\" name=\"thread\" value=\"1\"/>" >> /etc/ImageMagick-6/policy.xml
fi

# Clean up apt cache to save disk space
apt-get clean
rm -rf /var/lib/apt/lists/*

# Install Python dependencies with progress bar
echo "Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

# Install memory optimization libraries
echo "Installing memory optimization libraries..."
pip install --no-cache-dir -r memory_requirements.txt

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
