# VS Code Insiders Extensions Collection

A comprehensive collection of VS Code Insiders extensions with installation scripts for VS Code and Cursor IDE.

## Extension Overview
* Total number of extensions: 87
* Total size of all extensions: 1.8 GB

### Categories
* Cloud & DevOps: 28 extensions
* Programming Languages: 25 extensions
* Other: 20 extensions
* Remote Development: 11 extensions
* Development Tools: 2 extensions
* AI & Machine Learning: 1 extensions

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
* `install_gzipped_extensions.sh` - Special script for handling gzipped VSIX files
* `update_vsix_engine.py` - Updates VS Code engine versions in VSIX packages
* `fix_github_extensions.py` - Fixes GitHub extension compatibility issues
* `create_extension_db.py` - Creates extension inventory database and documentation

[See detailed script documentation](docs/index.md)
