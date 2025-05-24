# VS Code Insiders Extensions Collection

A comprehensive collection of VS Code Insiders extensions with installation scripts for VS Code and Cursor IDE. This repository provides tools for parallel installation, extension management, and compatibility fixes for VS Code version ^1.99.0.

## Extension Overview
* Total number of extensions: 87
* Total size of all extensions: 1.8 GB
* All extensions compatible with VS Code ^1.99.0

### Categories
* Cloud & DevOps: 28 extensions
* Programming Languages: 25 extensions
* Other: 20 extensions
* Remote Development: 11 extensions
* Development Tools: 2 extensions
* AI & Machine Learning: 1 extensions

[See detailed category breakdown](docs/categories.md)

## Quick Start Guide

### Standard Installation
```bash
# Install all extensions with the standard script
./scripts/install_cursor_extensions.sh
```

### Parallel Installation (Recommended)
```bash
# Install with OpenMPI (4 processes for faster installation)
mpiexec -n 4 python3 scripts/parallel_install_extensions.py
```

## Installation Methods

### Standard Installation
Uses a sequential installation process, installing one extension at a time:

```bash
# Standard installation with default options
./scripts/install_cursor_extensions.sh

# Install specific extensions only
./scripts/install_cursor_extensions.sh --extensions github.copilot,ms-python.python

# Install to a custom location
./scripts/install_cursor_extensions.sh --path /path/to/cursor/installation
```

### Parallel Installation with OpenMPI
Utilizes multiple processor cores for dramatically faster installation:

```bash
# Install using 4 parallel processes (recommended)
mpiexec -n 4 python3 scripts/parallel_install_extensions.py

# Install to a custom target directory
mpiexec -n 4 python3 scripts/parallel_install_extensions.py --target ~/.cursor/extensions

# Install from a specific source directory
mpiexec -n 4 python3 scripts/parallel_install_extensions.py --source ./extensions/new

# Skip backup of extensions.json
mpiexec -n 4 python3 scripts/parallel_install_extensions.py --skip-backup
```

## Performance Comparison

| Installation Method      | Time for 87 Extensions | Extensions/second |
|--------------------------|------------------------|-------------------|
| Parallel (4 processes)   | 22.5 seconds           | 3.9               |
| Standard (sequential)    | ~87 seconds            | 1.0               |
| Manual installation      | >10 minutes            | 0.1               |

Parallel installation is approximately 4x faster than the sequential method.

## Dependencies

### Base Requirements
- Git with LFS support (for cloning this repository)
- VS Code or Cursor IDE
- Bash shell environment
- `unzip` utility (for extension extraction)

### For Parallel Installation (OpenMPI)
```bash
# Ubuntu/Debian
sudo apt install openmpi-bin libopenmpi-dev
pip install mpi4py

# CentOS/RHEL
sudo yum install openmpi openmpi-devel
pip install mpi4py

# macOS
brew install open-mpi
pip install mpi4py
```

## Repository Structure

```
.
├── README.md                 # This file
├── db/                       # Database files
│   └── extension_inventory.db  # Extension metadata database
├── docs/                     # Documentation
│   ├── categories.md         # Extension categories
│   ├── category_*.md         # Category-specific docs
│   ├── extensions_by_size.md # Extensions by size
│   └── index.md              # Documentation index
├── extensions/               # Directory containing all .vsix extension files
├── logs/                     # Installation and operation logs
└── scripts/                  # Scripts directory
    ├── create_extension_db.py        # Database creation
    ├── download_extensions.sh        # Downloads extensions
    ├── fix_extensions_json.py        # Fixes extensions.json
    ├── fix_github_extensions.py      # Fixes GitHub extensions
    ├── install_cursor_extensions.sh  # Standard installer
    ├── install_gzipped_extensions.sh # Gzipped VSIX handler
    ├── parallel_install_extensions.py # OpenMPI installer
    └── update_vsix_engine.py         # Updates VS Code engine
```

## Available Scripts

* `parallel_install_extensions.py` - Fast parallel installer using OpenMPI (recommended)
* `install_cursor_extensions.sh` - Standard sequential installation script
* `install_gzipped_extensions.sh` - Special script for handling gzipped VSIX files
* `update_vsix_engine.py` - Updates VS Code engine versions in VSIX packages
* `fix_github_extensions.py` - Fixes GitHub extension compatibility issues
* `create_extension_db.py` - Creates extension inventory database and documentation
* `fix_extensions_json.py` - Fixes and normalizes extensions.json files

[See detailed script documentation](docs/index.md)

## Troubleshooting

### Common Issues

1. **Missing dependencies**: Ensure you have installed all required dependencies for your installation method.
2. **Permission issues**: Make sure scripts are executable (`chmod +x scripts/*.sh scripts/*.py`).
3. **OpenMPI errors**: Check that OpenMPI is properly installed and in your PATH.

For more detailed troubleshooting, check the logs in the `logs/` directory.
