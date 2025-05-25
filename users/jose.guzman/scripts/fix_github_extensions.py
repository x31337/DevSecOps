#!/usr/bin/env python3
import os
import sys
import json
import shutil
import zipfile
import tempfile
import logging
import datetime
import gzip
import subprocess
import threading
import time
from pathlib import Path
import re

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"github_extensions_fix_{timestamp}.log")

# Configure quiet logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
    ]
)

# Terminal output function with minimal information
def print_status(message, end="\n"):
    sys.stdout.write(message + end)
    sys.stdout.flush()

# Global progress tracking
total_extensions = 0
processed_extensions = 0
successful_fixes = 0
failed_fixes = 0

# Paths
EXTENSIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extensions")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extensions_backup")
SUCCESS_LOG = os.path.join(log_dir, f"github_fixed_extensions_{timestamp}.txt")
FAILED_LOG = os.path.join(log_dir, f"github_failed_extensions_{timestamp}.txt")

# Target extensions - the 4 GitHub extensions that failed previously
TARGET_EXTENSIONS = [
    "GitHub.vscode-codeql-1.17.2.vsix",
    "GitHub.vscode-github-actions-0.27.1.vsix",
    "GitHub.vscode-pull-request-github-0.110.0.vsix",
    "vscode.github-1.95.3.vsix"
]

def update_package_json(package_json_path, target_version="^1.99.0"):
    """Update the engines.vscode field in package.json."""
    try:
        with open(package_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Store original value for logging
        original_version = None
        if "engines" in data and "vscode" in data["engines"]:
            original_version = data["engines"]["vscode"]
        
        # Create or update the engines.vscode field
        if "engines" not in data:
            data["engines"] = {}
        data["engines"]["vscode"] = target_version
        
        # Write back the updated JSON
        with open(package_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        return True, original_version, target_version
    except Exception as e:
        logging.error(f"Error updating package.json: {e}")
        return False, None, None

def find_package_json(directory):
    """Find package.json file in the extracted directory structure."""
    for root, _, files in os.walk(directory):
        if "package.json" in files:
            return os.path.join(root, "package.json")
    return None

def update_progress():
    """Update the progress display."""
    global processed_extensions, total_extensions, successful_fixes, failed_fixes
    
    progress = processed_extensions / total_extensions if total_extensions > 0 else 0
    bar_length = 30
    filled_length = int(bar_length * progress)
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    
    print_status(f"\rProgress: [{bar}] {processed_extensions}/{total_extensions} | Success: {successful_fixes} | Failed: {failed_fixes}", end="")

def try_direct_zip_method(vsix_path, temp_dir):
    """Try to handle the extension as a direct ZIP file."""
    try:
        extraction_dir = os.path.join(temp_dir, "direct_zip")
        os.makedirs(extraction_dir, exist_ok=True)
        
        with zipfile.ZipFile(vsix_path, 'r') as zip_ref:
            zip_ref.extractall(extraction_dir)
            
        package_json_path = find_package_json(extraction_dir)
        if package_json_path:
            success, original, new = update_package_json(package_json_path)
            if success:
                # Repackage
                with zipfile.ZipFile(vsix_path, 'w', compression=zipfile.ZIP_DEFLATED) as zip_out:
                    for root, _, files in os.walk(extraction_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, extraction_dir)
                            zip_out.write(file_path, arcname)
                return True, original, new
        return False, None, None
    except Exception as e:
        logging.debug(f"Direct ZIP method failed: {e}")
        return False, None, None

def try_unzip_manually(vsix_path, temp_dir):
    """Try to extract using the unzip command line tool."""
    try:
        extraction_dir = os.path.join(temp_dir, "unzip_manual")
        os.makedirs(extraction_dir, exist_ok=True)
        
        # Use unzip command
        result = subprocess.run(
            ["unzip", "-q", "-o", vsix_path, "-d", extraction_dir], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            return False, None, None
            
        package_json_path = find_package_json(extraction_dir)
        if package_json_path:
            success, original, new = update_package_json(package_json_path)
            if success:
                # Use zip command to repackage
                current_dir = os.getcwd()
                os.chdir(extraction_dir)
                
                result = subprocess.run(
                    ["zip", "-q", "-r", os.path.join(temp_dir, "repacked.vsix"), "."],
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
                )
                
                os.chdir(current_dir)
                
                if result.returncode == 0:
                    shutil.copy2(os.path.join(temp_dir, "repacked.vsix"), vsix_path)
                    return True, original, new
        return False, None, None
    except Exception as e:
        logging.debug(f"Manual unzip method failed: {e}")
        return False, None, None

def try_vsce_method(vsix_path, temp_dir):
    """Try to use vsce to handle the VSIX."""
    try:
        # Check if vsce is installed
        result = subprocess.run(
            ["command", "-v", "vsce"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            shell=True
        )
        
        if result.returncode != 0:
            logging.debug("vsce not found, skipping this method")
            return False, None, None
        
        extraction_dir = os.path.join(temp_dir, "vsce_extract")
        os.makedirs(extraction_dir, exist_ok=True)
        
        # Try to extract with vsce
        result = subprocess.run(
            ["vsce", "ls", vsix_path], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            return False, None, None
        
        # Use unzip as a fallback since vsce doesn't have an extract command
        result = subprocess.run(
            ["unzip", "-q", "-o", vsix_path, "-d", extraction_dir], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            return False, None, None
            
        package_json_path = find_package_json(extraction_dir)
        if package_json_path:
            success, original, new = update_package_json(package_json_path)
            if success:
                # Try to repackage - we'll need to create a vsix from the extracted directory
                # Since this is complex with vsce, we'll use zip as a fallback
                current_dir = os.getcwd()
                os.chdir(extraction_dir)
                
                result = subprocess.run(
                    ["zip", "-q", "-r", os.path.join(temp_dir, "repacked.vsix"), "."],
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
                )
                
                os.chdir(current_dir)
                
                if result.returncode == 0:
                    shutil.copy2(os.path.join(temp_dir, "repacked.vsix"), vsix_path)
                    return True, original, new
        return False, None, None
    except Exception as e:
        logging.debug(f"vsce method failed: {e}")
        return False, None, None

def try_github_specific_format(vsix_path, temp_dir):
    """Try GitHub-specific format handling."""
    try:
        # This is a specialized method for GitHub extensions
        # First, we'll check if it's a standard VSIX with a .zip inside
        extraction_dir = os.path.join(temp_dir, "github_specific")
        os.makedirs(extraction_dir, exist_ok=True)
        
        # Some GitHub extensions are VSIXs with a specific structure
        with zipfile.ZipFile(vsix_path, 'r') as zip_ref:
            zip_contents = zip_ref.namelist()
            
            # Look for extension.vsixmanifest
            if 'extension.vsixmanifest' in zip_contents:
                zip_ref.extractall(extraction_dir)
                
                # Look for a package.json at the root or in an extension directory
                package_json_path = find_package_json(extraction_dir)
                if package_json_path:
                    success, original, new = update_package_json(package_json_path)
                    if success:
                        # Repackage
                        with zipfile.ZipFile(vsix_path, 'w', compression=zipfile.ZIP_DEFLATED) as zip_out:
                            for root, _, files in os.walk(extraction_dir):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    arcname = os.path.relpath(file_path, extraction_dir)
                                    zip_out.write(file_path, arcname)
                        return True, original, new
        
        return False, None, None
    except Exception as e:
        logging.debug(f"GitHub-specific format method failed: {e}")
        return False, None, None

def process_extension(vsix_path):
    """Process a single extension using multiple methods until one succeeds."""
    global processed_extensions, successful_fixes, failed_fixes
    
    extension_name = os.path.basename(vsix_path)
    logging.info(f"Processing: {extension_name}")
    
    # Create a temporary directory for extraction
    temp_dir = tempfile.mkdtemp(prefix="github_ext_fix_")
    
    try:
        # Try different methods in sequence
        methods = [
            ("Standard ZIP", try_direct_zip_method),
            ("Manual unzip", try_unzip_manually),
            ("VSCE tool", try_vsce_method),
            ("GitHub specific", try_github_specific_format)
        ]
        
        for method_name, method_func in methods:
            logging.info(f"Trying method: {method_name}")
            success, original, new = method_func(vsix_path, temp_dir)
            
            if success:
                logging.info(f"Successfully updated {extension_name} using {method_name} method")
                logging.info(f"Engine version changed from {original} to {new}")
                
                with open(SUCCESS_LOG, "a") as f:
                    f.write(f"{extension_name}: {original} -> {new} (using {method_name})\n")
                
                successful_fixes += 1
                processed_extensions += 1
                update_progress()
                return True
        
        # If we get here, all methods failed
        logging.error(f"All methods failed for {extension_name}")
        with open(FAILED_LOG, "a") as f:
            f.write(f"{extension_name}: All methods failed\n")
        
        failed_fixes += 1
        processed_extensions += 1
        update_progress()
        return False
        
    except Exception as e:
        logging.error(f"Error processing {extension_name}: {e}")
        with open(FAILED_LOG, "a") as f:
            f.write(f"{extension_name}: {str(e)}\n")
        
        failed_fixes += 1
        processed_extensions += 1
        update_progress()
        return False
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)

def process_extensions():
    """Process all target extensions."""
    global total_extensions
    
    # Initialize log files
    for log_path in [FAILED_LOG, SUCCESS_LOG]:
        with open(log_path, "w") as f:
            f.write(f"# Log generated on {datetime.datetime.now().isoformat()}\n")
    
    # Get all target extension paths
    vsix_files = []
    for ext in TARGET_EXTENSIONS:
        path = os.path.join(EXTENSIONS_DIR, ext)
        if os.path.exists(path):
            vsix_files.append(path)
    
    total_extensions = len(vsix_files)
    if total_extensions == 0:
        print_status("No target extensions found.")
        return
    
    print_status(f"Found {total_extensions} GitHub extensions to process.")
    update_progress()
    
    # Process each extension
    for vsix_path in vsix_files:
        process_extension(vsix_path)
    
    # Print final summary
    print_status("\n\nProcessing complete!")
    print_status(f"Successfully fixed: {successful_fixes}/{total_extensions}")
    print_status(f"Failed: {failed_fixes}/{total_extensions}")
    print_status(f"Detailed logs available at: {log_file}")

def main():
    """Main entry point."""
    print_status(f"Starting GitHub extensions fix script...")
    
    # Ensure backup exists
    if not os.path.exists(BACKUP_DIR):
        print_status(f"Warning: Backup directory {BACKUP_DIR} does not exist.")
        response = input("Continue without backup? (y/n): ")
        if response.lower() != 'y':
            print_status("Aborting.")
            sys.exit(1)
    
    # Start processing in a background thread
    thread = threading.Thread(target=process_extensions)
    thread.daemon = True
    thread.start()
    
    # Wait for processing to complete, but allow keyboard interrupt
    try:
        while thread.is_alive():
            thread.join(0.5)
    except KeyboardInterrupt:
        print_status("\nProcess interrupted by user.")
        sys.exit(1)

if __name__ == "__main__":
    main()

