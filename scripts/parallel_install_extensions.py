#!/usr/bin/env python3
"""
Parallel extension installer using OpenMPI to speed up installation.
Requires mpi4py and OpenMPI to be installed:

  pip install mpi4py
  # On Ubuntu/Debian
  apt install openmpi-bin libopenmpi-dev
  # On CentOS/RHEL
  yum install openmpi openmpi-devel
  # On macOS
  brew install open-mpi

Run with:
  mpiexec -n <num_processes> python3 parallel_install_extensions.py [OPTIONS]

Example:
  mpiexec -n 4 python3 parallel_install_extensions.py --source ./extensions
"""

import os
import sys
import time
import gzip
import json
import shutil
import zipfile
import tempfile
import argparse
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any

try:
    from mpi4py import MPI
except ImportError:
    print("ERROR: mpi4py is required. Install with: pip install mpi4py")
    print("Also ensure OpenMPI is installed on your system.")
    sys.exit(1)

# MPI initialization
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Get current directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Configuration
DEFAULT_EXTENSIONS_DIR = os.path.join(PROJECT_ROOT, "extensions")
CURSOR_EXTENSIONS_DIR = os.path.expanduser("~/.cursor/extensions")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"parallel_install_{TIMESTAMP}_rank{rank}.log")
MASTER_LOG_FILE = os.path.join(LOG_DIR, f"parallel_install_{TIMESTAMP}_master.log")
SUCCESS_FILE = os.path.join(LOG_DIR, f"parallel_install_{TIMESTAMP}_success.txt")
ERROR_FILE = os.path.join(LOG_DIR, f"parallel_install_{TIMESTAMP}_errors.txt")

# Terminal colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
ENDC = '\033[0m'
BOLD = '\033[1m'

# Setup logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='[Rank %(rank)d] %(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout) if rank == 0 else logging.NullHandler()
    ]
)
logger = logging.getLogger()
logger = logging.LoggerAdapter(logger, {"rank": rank})

# Only master process handles terminal output
def master_print(msg, end='\n', color=None):
    if rank == 0:
        if color:
            print(f"{color}{msg}{ENDC}", end=end)
        else:
            print(msg, end=end)
        sys.stdout.flush()

def log_to_master(msg, level="INFO"):
    """Log to master process log file"""
    if rank == 0:
        with open(MASTER_LOG_FILE, 'a') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {level}: {msg}\n")

def is_gzipped(file_path: str) -> bool:
    """Check if a file is gzipped by looking at its magic number."""
    try:
        with open(file_path, 'rb') as f:
            return f.read(2) == b'\x1f\x8b'
    except Exception:
        return False

def extract_vsix(vsix_path: str, target_dir: str) -> bool:
    """Extract a VSIX file, handling both regular and gzipped files."""
    temp_dir = tempfile.mkdtemp()
    temp_file = None
    
    try:
        # Check if file is gzipped
        if is_gzipped(vsix_path):
            logger.info(f"Detected gzipped file: {vsix_path}")
            temp_file = os.path.join(temp_dir, "decompressed.zip")
            
            with gzip.open(vsix_path, 'rb') as f_in:
                with open(temp_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            vsix_to_extract = temp_file
        else:
            vsix_to_extract = vsix_path
        
        # Extract the VSIX (zip) file
        with zipfile.ZipFile(vsix_to_extract, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to extract {vsix_path}: {str(e)}")
        return False
    
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def get_extension_id_version(vsix_path: str) -> Tuple[str, str]:
    """Extract extension ID and version from filename."""
    filename = os.path.basename(vsix_path)
    
    # Pattern 1: publisher.name@version.vsix
    if '@' in filename:
        parts = filename.split('@', 1)
        extension_id = parts[0]
        version = parts[1].rsplit('.', 1)[0]  # Remove .vsix extension
        return extension_id, version
    
    # Pattern 2: Publisher.name-version.vsix
    if '-' in filename:
        parts = filename.rsplit('-', 1)
        if len(parts) == 2:
            extension_id = parts[0]
            version = parts[1].rsplit('.', 1)[0]  # Remove .vsix extension
            return extension_id, version
    
    # If we can't parse, return defaults
    return os.path.splitext(filename)[0], "unknown"

def install_extension(vsix_path: str, target_dir: str) -> bool:
    """Install a single extension."""
    extension_id, version = get_extension_id_version(vsix_path)
    ext_target_dir = os.path.join(target_dir, f"{extension_id}-{version}")
    
    # Create target directory
    os.makedirs(ext_target_dir, exist_ok=True)
    
    # Extract VSIX to target directory
    return extract_vsix(vsix_path, ext_target_dir)

def find_extensions(source_dir: str) -> List[str]:
    """Find all .vsix files in the source directory."""
    extensions = []
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.vsix'):
                extensions.append(os.path.join(root, file))
    return sorted(extensions)

def distribute_extensions(extensions: List[str]) -> List[str]:
    """Distribute extensions among processes."""
    # Calculate the extensions each process will handle
    num_extensions = len(extensions)
    chunk_size = num_extensions // size
    remainder = num_extensions % size
    
    # Calculate start and end indices for this rank
    start_idx = rank * chunk_size + min(rank, remainder)
    end_idx = start_idx + chunk_size + (1 if rank < remainder else 0)
    
    # Get this rank's extensions
    return extensions[start_idx:end_idx]

def process_extensions(extensions: List[str], target_dir: str) -> Tuple[List[str], List[str]]:
    """Process a list of extensions assigned to this rank."""
    success_list = []
    error_list = []
    
    total = len(extensions)
    for i, ext_path in enumerate(extensions, 1):
        ext_name = os.path.basename(ext_path)
        logger.info(f"[{i}/{total}] Installing: {ext_name}")
        
        try:
            if install_extension(ext_path, target_dir):
                success_list.append(ext_path)
                logger.info(f"Successfully installed: {ext_name}")
            else:
                error_list.append(ext_path)
                logger.error(f"Failed to install: {ext_name}")
        except Exception as e:
            error_list.append(ext_path)
            logger.error(f"Error installing {ext_name}: {str(e)}")
    
    return success_list, error_list

def backup_extensions_json(target_dir: str) -> bool:
    """Backup the extensions.json file if it exists."""
    extensions_json = os.path.join(target_dir, "extensions.json")
    if os.path.exists(extensions_json):
        backup_file = f"{extensions_json}.backup.{TIMESTAMP}"
        try:
            shutil.copy2(extensions_json, backup_file)
            logger.info(f"Backed up extensions.json to {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup extensions.json: {str(e)}")
            return False
    return True  # No file to backup is also success

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Parallel VS Code extension installer')
    parser.add_argument('--source', default=DEFAULT_EXTENSIONS_DIR,
                        help='Source directory containing VSIX files')
    parser.add_argument('--target', default=CURSOR_EXTENSIONS_DIR,
                        help='Target directory where extensions will be installed')
    parser.add_argument('--skip-backup', action='store_true',
                        help='Skip backing up extensions.json')
    parser.add_argument('--force', action='store_true',
                        help='Force reinstallation of extensions')
    
    args = parser.parse_args()
    
    # Master process prints banner
    if rank == 0:
        master_print(f"\n{BOLD}{'=' * 60}{ENDC}")
        master_print(f"{BOLD}{BLUE}     Parallel VS Code Extension Installer (MPI){ENDC}")
        master_print(f"{BOLD}{'=' * 60}{ENDC}\n")
        master_print(f"Using {BOLD}{size}{ENDC} MPI processes for parallel installation")
        master_print(f"Source: {BOLD}{args.source}{ENDC}")
        master_print(f"Target: {BOLD}{args.target}{ENDC}\n")
        
        # Create target directory if it doesn't exist
        os.makedirs(args.target, exist_ok=True)
        
        # Backup extensions.json
        if not args.skip_backup:
            backup_extensions_json(args.target)
        
        # Create log files
        with open(MASTER_LOG_FILE, 'w') as f:
            f.write(f"# Parallel Installation Log - {datetime.now().isoformat()}\n")
            f.write(f"# Using {size} MPI processes\n")
            f.write(f"# Source: {args.source}\n")
            f.write(f"# Target: {args.target}\n\n")
        
        with open(SUCCESS_FILE, 'w') as f:
            f.write(f"# Successfully installed extensions - {datetime.now().isoformat()}\n\n")
        
        with open(ERROR_FILE, 'w') as f:
            f.write(f"# Failed extensions - {datetime.now().isoformat()}\n\n")
    
    # Synchronize processes before continuing
    comm.Barrier()
    
    # Master process finds all extensions
    if rank == 0:
        all_extensions = find_extensions(args.source)
        master_print(f"Found {BOLD}{len(all_extensions)}{ENDC} extensions to process")
        log_to_master(f"Found {len(all_extensions)} extensions to process")
    else:
        all_extensions = None
    
    # Broadcast the list of extensions to all processes
    all_extensions = comm.bcast(all_extensions, root=0)
    
    # Each process determines its portion of extensions
    my_extensions = distribute_extensions(all_extensions)
    logger.info(f"Process will handle {len(my_extensions)} extensions")
    
    # Process extensions
    start_time = time.time()
    success_list, error_list = process_extensions(my_extensions, args.target)
    end_time = time.time()
    
    # Each process reports its results
    process_results = {
        'rank': rank,
        'total': len(my_extensions),
        'success': len(success_list),
        'error': len(error_list),
        'time': end_time - start_time,
        'success_list': success_list,
        'error_list': error_list
    }
    
    # Gather results from all processes
    all_results = comm.gather(process_results, root=0)
    
    # Master process handles final reporting
    if rank == 0:
        total_extensions = len(all_extensions)
        total_success = sum(r['success'] for r in all_results)
        total_errors = sum(r['error'] for r in all_results)
        max_time = max(r['time'] for r in all_results)
        
        # Write successful extensions to file
        with open(SUCCESS_FILE, 'a') as f:
            for r in all_results:
                for ext in r['success_list']:
                    f.write(f"{ext}\n")
        
        # Write failed extensions to file
        with open(ERROR_FILE, 'a') as f:
            for r in all_results:
                for ext in r['error_list']:
                    f.write(f"{ext}\n")
        
        # Report summary
        master_print(f"\n{BOLD}{'=' * 60}{ENDC}")
        master_print(f"{BOLD}Installation Summary{ENDC}")
        master_print(f"{BOLD}{'=' * 60}{ENDC}")
        master_print(f"Total extensions processed: {BOLD}{total_extensions}{ENDC}")
        master_print(f"Successfully installed: {BOLD}{GREEN}{total_success}{ENDC}")
        master_print(f"Failed: {BOLD}{RED}{total_errors}{ENDC}")
        master_print(f"Time taken: {BOLD}{max_time:.2f}{ENDC} seconds")
        master_print(f"Average time per extension: {BOLD}{(max_time / total_extensions):.2f}{ENDC} seconds")
        master_print(f"\nDetailed logs: {BOLD}{LOG_DIR}{ENDC}")
        master_print(f"Success list: {BOLD}{SUCCESS_FILE}{ENDC}")
        master_print(f"Error list: {BOLD}{ERROR_FILE}{ENDC}")
        
        log_to_master(f"Installation completed. Success: {total_success}, Failed: {total_errors}, Time: {max_time:.2f}s")
        
        if total_errors > 0:
            master_print(f"\n{YELLOW}Warning: Some extensions failed to install. See error log for details.{ENDC}")
            return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        if rank == 0:
            master_print(f"\n{RED}Installation interrupted by user{ENDC}")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        sys.exit(1)

