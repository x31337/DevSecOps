# VS Code Insiders Extensions Collection

A comprehensive collection of VS Code Insiders extensions with installation scripts for VS Code and Cursor IDE.

## Repository Structure

```
.
├── README.md                 # This file
├── LICENSE                   # License information
├── extensions/               # Directory containing all .vsix extension files
├── logs/                     # Installation logs and extension lists
│   ├── cursor_extension_install_*.log   # Installation logs
│   ├── extensions_with_versions.txt     # List of extensions with versions
│   └── failed_downloads.txt             # Any failed download attempts
└── scripts/                  # Installation and utility scripts
    ├── download_extensions.sh           # Script to download extensions
    ├── install_extensions_cursor.sh     # Basic Cursor IDE installation script
    └── install_extensions_cursor_new.sh # Advanced Cursor IDE installation script
```

## Extension Overview
* Total number of extensions: 67
* Total size of all extensions: 1.1G

## Installation Instructions

### Prerequisites
- Git with LFS support (for cloning this repository)
- VS Code or Cursor IDE
- Bash shell environment
- `unzip` utility (for extension installation)
- Optional: `jq` utility (for better JSON handling)

### Cloning the Repository

This repository uses Git LFS to manage large files. To clone:

```bash
# Install Git LFS if you don't have it
# Ubuntu/Debian: sudo apt-get install git-lfs
# macOS: brew install git-lfs
# Windows: download from https://git-lfs.github.com/

# Setup Git LFS
git lfs install

# Clone the repository
git clone https://github.com/x31337/DevSecOps.git
cd DevSecOps
```

### Installing Extensions in Cursor IDE

For Cursor IDE, use one of the provided installation scripts:

```bash
# Make script executable if needed
chmod +x scripts/install_extensions_cursor_new.sh

# Run the installation script
./scripts/install_extensions_cursor_new.sh

# Restart Cursor IDE after installation
```

The script will:
1. Analyze currently installed extensions
2. Compare with available extensions
3. Install only missing or newer versions
4. Provide detailed progress information

### Installing Extensions in VS Code

To install in regular VS Code:

```bash
# Install a specific extension
code --install-extension extensions/[extension-file-name].vsix

# Or use a simple loop to install all extensions
for ext in extensions/*.vsix; do
    code --install-extension "$ext"
done
```

## Available Scripts

### download_extensions.sh
Downloads VS Code Insider extensions from the marketplace.

### install_extensions_cursor.sh
Basic script to install extensions in Cursor IDE. Uses the Cursor AppImage to install extensions.

### install_extensions_cursor_new.sh
Advanced script for Cursor IDE installation with improved features:
- Detects already installed extensions
- Handles binary .vsix files correctly
- Updates extensions.json with proper metadata
- Creates minimal package.json for each extension
- Supports version comparison and updates

## Extension Categories
* Development Tools: GitHub Copilot, Azure Tools, Python Tools
* Language Support: Python, C#, Java, TypeScript, etc.
* Remote Development: Containers, WSL, SSH
* Cloud Services: Azure, Kubernetes
* Language Packs: Spanish, Chinese

## Key Extensions
* GitHub Copilot and related tools
* Azure Development Suite
* Python Development Tools (including Pylance)
* Remote Development Pack
* Container and Kubernetes Tools
* .NET and C# Development Tools

## Notable Extensions by Size
### Largest Extensions:
* ms-vscode.vscode-speech (166MB)
* ms-dotnettools.csharp (185MB)
* googlecloudtools.cloudcode (157MB)
* google.geminicodeassist (148MB)
* ms-azuretools.vscode-azure-github-copilot (147MB)

### Development Essentials:
* github.copilot (16MB)
* github.copilot-chat (5.1MB)
* ms-python.python (9.9MB)
* ms-python.vscode-pylance (24MB)
* eamodio.gitlens (8.4MB)

## Git LFS Usage

This repository uses Git Large File Storage (LFS) to manage the VS Code extension files (.vsix), many of which exceed GitHub's standard file size limits. The benefits include:

- Efficient handling of large binary files
- Reduced repository size for normal operations
- Faster clones when using `--depth` options

When cloning, make sure Git LFS is installed first to properly download the extension files. Without Git LFS, you'll only get pointer files instead of the actual extension content.

The `.gitattributes` file is configured to track all `.vsix` files with Git LFS automatically.
