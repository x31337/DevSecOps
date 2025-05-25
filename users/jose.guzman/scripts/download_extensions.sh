#!/bin/bash

EXTENSIONS_FILE=~/Downloads/vscodeinsidersextensions/extensions_with_versions.txt
OUTPUT_DIR=~/Downloads/vscodeinsidersextensions

# Create a log file for failed downloads
touch "$OUTPUT_DIR/failed_downloads.txt"

while IFS=@ read -r extension version; do
    echo "Processing $extension@$version"
    
    # Clean up the version string (remove any whitespace)
    version=$(echo "$version" | tr -d '[:space:]')
    
    # Create a safe filename
    safe_filename=$(echo "$extension@$version.vsix" | tr '/' '-')
    output_file="$OUTPUT_DIR/$safe_filename"
    
    # Try VS Code Marketplace first
    echo "Trying VS Code Marketplace..."
    curl -L -o "$output_file" "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/${extension%%.*}/vsextensions/${extension#*.}/$version/vspackage"
    
    # If VS Code Marketplace failed, try open-vsx.org
    if [ $? -ne 0 ] || [ ! -s "$output_file" ]; then
        echo "VS Code Marketplace failed, trying open-vsx.org..."
        curl -L -o "$output_file" "https://open-vsx.org/api/${extension%%.*}/${extension#*.}/$version/file/${extension%%.*}.${extension#*.}-$version.vsix"
        
        # If both failed, add to failed downloads list
        if [ $? -ne 0 ] || [ ! -s "$output_file" ]; then
            echo "$extension@$version" >> "$OUTPUT_DIR/failed_downloads.txt"
            rm -f "$output_file"
            echo "Failed to download $extension@$version"
            continue
        fi
    fi
    
    echo "Successfully downloaded $safe_filename"
done < "$EXTENSIONS_FILE"

echo "Download complete. Check failed_downloads.txt for any failures."
