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
    ├── fix_extensions_json.py           # Script to fix and normalize extensions.json
    ├── fix_github_extensions.py         # Script to fix GitHub extension compatibility
    ├── install_cursor_extensions.sh     # Comprehensive Cursor IDE installation script
    └── update_vsix_engine.py            # Script to update VSIX engine versions
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

For Cursor IDE, use the provided installation script:

```bash
# Make script executable if needed
chmod +x scripts/install_cursor_extensions.sh

# Run the installation script with default options
./scripts/install_cursor_extensions.sh

# Or specify options for more control
./scripts/install_cursor_extensions.sh --path /path/to/cursor --source ./extensions --verbose

# Restart Cursor IDE after installation
```

The script supports multiple options:
```
  -h, --help             Show help message and exit
  -p, --path PATH        Specify Cursor installation path
  -s, --source DIR       Specify source extensions directory
  -e, --extensions LIST  Comma-separated list of extensions to install
  -y, --yes              Auto-confirm all prompts
  -q, --quiet            Minimal output mode
  -v, --verbose          Verbose output mode
  -d, --debug            Debug mode with extra information
  --dry-run              Simulate installation without making changes
```

The script will:
1. Detect Cursor IDE installation automatically
2. Analyze currently installed extensions
3. Compare with available extensions
4. Install only missing or newer versions
5. Provide detailed progress with a visual progress bar
6. Create comprehensive logs for troubleshooting

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

### install_cursor_extensions.sh
Comprehensive script for installing extensions in Cursor IDE:

- **Platform Support**: 
  - Automatically detects Cursor on Linux and macOS
  - Handles different installation locations
  - Supports custom paths with `--path` option

- **Smart Installation**:
  - Detects already installed extensions
  - Handles binary .vsix files correctly
  - Updates extensions.json with proper metadata
  - Creates minimal package.json for each extension
  - Supports version comparison and only updates when needed

### fix_extensions_json.py
Script to fix and normalize the Cursor IDE's extensions.json file:
- Normalizes extension IDs and directory structures
- Handles special cases for GitHub extensions
- Creates backups of the original extensions.json
- Maintains proper version tracking
- Provides detailed processing statistics

### fix_github_extensions.py
Specialized script for fixing GitHub extension compatibility issues:
- Focuses on problematic GitHub extensions
- Uses multiple extraction and repacking methods
- Updates engine version requirements
- Provides detailed logging and progress tracking
- Creates backups before modifications

### update_vsix_engine.py
General-purpose script for updating VS Code engine versions in VSIX packages:
- Processes VSIX files to update engine compatibility
- Handles both ZIP and GZIP compression
- Updates package.json engine requirements
- Creates detailed logs of all changes
- Provides progress tracking and success/failure statistics

- **Flexible Options**:
  - Install all extensions or select specific ones with `--extensions`
  - Debug mode for troubleshooting
  - Dry-run mode to simulate without changes
  - Quiet mode for CI/CD integration
  - Verbose mode for detailed information

- **User Experience**:
  - Visual progress bar during installation
  - Color-coded status messages
  - Detailed logs for troubleshooting
  - Comprehensive error handling

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
