# VS Code Insiders Extensions Collection

A comprehensive collection of VS Code Insiders extensions with installation scripts for VS Code and Cursor IDE.

## Repository Structure

```
.
├── README.md                 # This file
├── LICENSE                   # License information
├── docs/                     # Detailed documentation
│   ├── index.md              # Documentation index
│   ├── categories.md         # Extension categories
│   ├── extensions_by_size.md # Extensions sorted by size
│   └── category_*.md         # Category-specific documentation
├── extension_inventory.db    # Extension metadata database
├── extensions/               # Directory containing all .vsix extension files
├── logs/                     # Installation logs and extension lists
│   ├── cursor_extension_install_*.log   # Installation logs
│   ├── extensions_with_versions.txt     # List of extensions with versions
│   └── failed_downloads.txt             # Any failed download attempts
└── scripts/                  # Installation and utility scripts
    ├── create_extension_db.py          # Script to create extension inventory
    ├── download_extensions.sh          # Script to download extensions
    ├── fix_extensions_json.py          # Script to fix and normalize extensions.json
    ├── fix_github_extensions.py        # Script to fix GitHub extension compatibility
    ├── install_cursor_extensions.sh    # Comprehensive Cursor IDE installation script
    └── update_vsix_engine.py           # Script to update VSIX engine versions
```

## Extension Overview
* Total number of extensions: 67
* Total size of all extensions: 1.1 GB

### Categories
* Programming Languages: 30 extensions
* Cloud & DevOps: 16 extensions
* Development Tools: 9 extensions
* Other: 5 extensions
* Remote Development: 4 extensions
* AI & Machine Learning: 3 extensions

[See detailed category breakdown](docs/categories.md)

## Installation Instructions

### Prerequisites
- Git with LFS support (for cloning this repository)
- VS Code or Cursor IDE
- Bash shell environment
- `unzip` utility (for extension installation)

### Installing Extensions in Cursor IDE

```bash
# Run the installation script with default options
./scripts/install_cursor_extensions.sh
```

[See detailed installation instructions](docs/index.md)

## Available Scripts

* `install_cursor_extensions.sh` - Comprehensive installation script for Cursor IDE
* `download_extensions.sh` - Downloads VS Code extensions from the marketplace
* `create_extension_db.py` - Creates extension inventory database and documentation
* `fix_extensions_json.py` - Fixes and normalizes extensions.json files
* `fix_github_extensions.py` - Fixes GitHub extension compatibility issues
* `update_vsix_engine.py` - Updates VS Code engine versions in VSIX packages

[See detailed script documentation](docs/index.md)

