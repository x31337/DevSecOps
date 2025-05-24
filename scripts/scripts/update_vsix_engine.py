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
from pathlib import Path
import subprocess
import re

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(log_dir, exist_ok=True)

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"vsix_update_{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

# Summary counters
total_extensions = 0
successful_updates = 0
failed_updates = 0
skipped_extensions = 0

# Configure paths
EXTENSIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "extensions")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "extensions_backup")
FAILED_LOG = os.path.join(log_dir, f"failed_extensions_{timestamp}.txt")
SUCCESS_LOG = os.path.join(log_dir, f"successful_extensions_{timestamp}.txt")

# List of extensions to focus on updating (incompatible ones from the marketplace)
TARGET_EXTENSIONS = [
    "apidev.azure-api-center",
    "github.copilot",
    "github.copilot-chat",
    "github.vscode-pull-request-github",
    "ms-azure-load-testing.microsoft-testing",
    "ms-azuretools.vscode-azure-github-copilot",
    "ms-dotnettools.vscode-dotnet-runtime",
    "ms-kubernetes-tools.vscode-kubernetes-tools",
    "ms-vscode-remote.remote-wsl",
    "vscjava.vscode-java-upgrade"
]


def find_package_json(directory):
    """Find package.json file in the extracted directory structure."""
    for root, _, files in os.walk(directory):
        if "package.json" in files:
            return os.path.join(root, "package.json")
    return None


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


def process_vsix_file(vsix_path):
    """Process a single VSIX file to update the engines.vscode field."""
    global successful_updates, failed_updates, skipped_extensions
    
    extension_name = os.path.basename(vsix_path)
    logging.info(f"Processing: {extension_name}")
    
    # Create a temporary directory for extraction
    temp_dir = tempfile.mkdtemp(prefix="vsix_update_")
    temp_output_dir = tempfile.mkdtemp(prefix="vsix_repackage_")
    
    # Create temporary files for handling different formats
    temp_extracted_file = os.path.join(temp_dir, "extracted.zip")
    temp_recompressed_file = os.path.join(temp_output_dir, "recompressed.vsix")
    extraction_dir = os.path.join(temp_dir, "contents")
    os.makedirs(extraction_dir, exist_ok=True)
    
    extraction_success = False
    is_gzipped = False
    
    try:
        # Method 1: Try to handle as a gzipped file first
        try:
            logging.debug(f"Attempting to extract {extension_name} as a GZIP file")
            with gzip.open(vsix_path, 'rb') as f_in:
                with open(temp_extracted_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Now try to open the extracted content as a ZIP file
            with zipfile.ZipFile(temp_extracted_file, 'r') as zip_ref:
                zip_ref.extractall(extraction_dir)
                extraction_success = True
                is_gzipped = True
                logging.debug(f"Successfully extracted {extension_name} as a GZIP+ZIP file")
        except (gzip.BadGzipFile, zipfile.BadZipFile, OSError) as err:
            logging.debug(f"GZIP extraction failed for {extension_name}: {str(err)}")
            # If the gzip method failed, we'll try the direct ZIP method next
            
        # Method 2: Try direct ZIP extraction if GZIP method failed
        if not extraction_success:
            try:
                logging.debug(f"Attempting to extract {extension_name} as a direct ZIP file")
                with zipfile.ZipFile(vsix_path, 'r') as zip_ref:
                    zip_ref.extractall(extraction_dir)
                    extraction_success = True
                    is_gzipped = False
                    logging.debug(f"Successfully extracted {extension_name} as a direct ZIP file")
            except zipfile.BadZipFile:
                logging.warning(f"Could not extract {extension_name} as either GZIP or ZIP file")
        
        # If extraction failed through both methods, return basic metadata
        if not extraction_success:
            logging.error(f"Could not extract {extension_name}")
            failed_updates += 1
            with open(FAILED_LOG, "a") as f:
                f.write(f"{extension_name}: Could not extract file\n")
            return False
        
        # Find the package.json file
        package_json_path = find_package_json(extraction_dir)
        if not package_json_path:
            logging.warning(f"No package.json found in {extension_name}")
            skipped_extensions += 1
            with open(FAILED_LOG, "a") as f:
                f.write(f"{extension_name}: No package.json found\n")
            return False
        
        # Update the package.json file
        success, original_version, new_version = update_package_json(package_json_path)
        if not success:
            logging.error(f"Failed to update package.json in {extension_name}")
            failed_updates += 1
            with open(FAILED_LOG, "a") as f:
                f.write(f"{extension_name}: Failed to update package.json\n")
            return False
        
        # Create a new ZIP file with the updated content
        updated_zip_file = os.path.join(temp_output_dir, "updated.zip")
        with zipfile.ZipFile(updated_zip_file, 'w', compression=zipfile.ZIP_DEFLATED) as zip_out:
            for root, _, files in os.walk(extraction_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, extraction_dir)
                    zip_out.write(file_path, arcname)
        
        # If the original was a gzip file, recompress the updated ZIP as gzip
        if is_gzipped and extraction_success:
            logging.debug(f"Recompressing {extension_name} as GZIP")
            with open(updated_zip_file, 'rb') as f_in:
                with gzip.open(temp_recompressed_file, 'wb', compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            output_file = temp_recompressed_file
        else:
            # If it was a regular ZIP, just use the updated ZIP directly
            logging.debug(f"Using direct ZIP for {extension_name}")
            output_file = updated_zip_file
        
        # Replace the original VSIX with the updated one
        shutil.copy2(output_file, vsix_path)
        
        # Log the successful update
        logging.info(f"Successfully updated {extension_name}: vscode engine {original_version} -> {new_version}")
        successful_updates += 1
        with open(SUCCESS_LOG, "a") as f:
            f.write(f"{extension_name}: {original_version} -> {new_version}\n")
        
        return True
        
    except gzip.BadGzipFile:
        logging.error(f"The file {extension_name} is not a valid gzip file")
        failed_updates += 1
        with open(FAILED_LOG, "a") as f:
            f.write(f"{extension_name}: Not a valid gzip file\n")
        return False
    except Exception as e:
        logging.error(f"Error processing {extension_name}: {e}")
        failed_updates += 1
        with open(FAILED_LOG, "a") as f:
            f.write(f"{extension_name}: {str(e)}\n")
        return False
        
    finally:
        # Clean up temporary directories
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(temp_output_dir, ignore_errors=True)


def main():
    global total_extensions
    
    # Ensure backup exists
    if not os.path.exists(BACKUP_DIR):
        logging.error(f"Backup directory {BACKUP_DIR} does not exist. Please create backups first.")
        sys.exit(1)
    
    # Initialize log files
    for log_path in [FAILED_LOG, SUCCESS_LOG]:
        with open(log_path, "w") as f:
            f.write(f"# Log generated on {datetime.datetime.now().isoformat()}\n")
    
    # Get VSIX files to process (filter to target extensions if specified)
    all_vsix_files = sorted([os.path.join(EXTENSIONS_DIR, f) for f in os.listdir(EXTENSIONS_DIR) if f.endswith('.vsix')])
    
    # Filter to target extensions
    vsix_files = []
    for vsix_path in all_vsix_files:
        filename = os.path.basename(vsix_path)
        for target in TARGET_EXTENSIONS:
            if target in filename:
                vsix_files.append(vsix_path)
                break
    
    total_extensions = len(vsix_files)
    
    if total_extensions == 0:
        logging.error(f"No matching VSIX files found in {EXTENSIONS_DIR}")
        sys.exit(1)
    
    logging.info(f"Found {total_extensions} VSIX files to process (from {len(all_vsix_files)} total)")
    
    # Process each VSIX file
    for i, vsix_path in enumerate(vsix_files, 1):
        logging.info(f"[{i}/{total_extensions}] Processing {os.path.basename(vsix_path)}")
        process_vsix_file(vsix_path)
    
    # Print summary
    logging.info("\n=== Processing Summary ===")
    logging.info(f"Total extensions processed: {total_extensions}")
    logging.info(f"Successfully updated: {successful_updates}")
    logging.info(f"Failed to update: {failed_updates}")
    logging.info(f"Skipped extensions: {skipped_extensions}")
    logging.info(f"Detailed logs available at: {log_file}")
    logging.info(f"Successfully updated extensions list: {SUCCESS_LOG}")
    logging.info(f"Failed extensions list: {FAILED_LOG}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
        sys.exit(1)

