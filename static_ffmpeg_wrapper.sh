#!/bin/bash
# This is a dummy ffmpeg wrapper that doesn't actually process video
# It's used for Render free tier to avoid memory issues

echo "STATIC FFMPEG: Memory-saving mode active"
echo "Arguments received: $@"

# Parse arguments to find output file
output_file=""
prev_arg=""
for arg in "$@"; do
  if [[ "$prev_arg" == "-i" ]]; then
    input_file="$arg"
  fi
  
  # Check if this is an output file (not starting with dash)
  if [[ "$arg" != -* && "$arg" == *"."* ]]; then
    output_file="$arg"
  fi
  
  prev_arg="$arg"
done

# Create an extremely small static video file
if [[ -n "$output_file" ]]; then
  echo "Creating static output file: $output_file"
  # Create directory if it doesn't exist
  mkdir -p $(dirname "$output_file")
  
  # If output is image pipe, create a tiny pixel image
  if [[ "$output_file" == "-" ]]; then
    # Output a single pixel (1x1) RGB image
    echo -e "\x00\x00\x00" # One black pixel
  else
    # Create a minimal file that won't consume memory
    echo "This is a static video placeholder to avoid memory issues on Render free tier." > "$output_file"
  fi
fi

# Exit successfully to avoid errors in calling code
exit 0
