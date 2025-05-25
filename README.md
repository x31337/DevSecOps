# VS Code Insiders Extensions Collection

A comprehensive collection of VS Code Insiders extensions with installation scripts for VS Code and Cursor IDE. This repository provides tools for parallel installation, extension management, and compatibility fixes for VS Code version ^1.99.0.

## Extension Overview
* Total number of extensions: 67
* Total size of all extensions: 1.8 GB
* All extensions compatible with VS Code ^1.99.0

### Categories
* Cloud & DevOps: 19 extensions
  - Azure tools, Cloud services, Kubernetes, Containers
* Programming Languages: 16 extensions
  - Python, Java, C#, TypeScript, Go, Rust, etc.
* Other: 15 extensions
  - Various utility and enhancement extensions
* Remote Development: 9 extensions
  - Remote workspace, SSH, WSL, Codespaces
* AI & Machine Learning: 6 extensions
  - Copilot, ChatGPT, Gemini, AI tooling
* Development Tools: 2 extensions
  - Testing, Linting, Debugging tools

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

| Installation Method      | Time for 67 Extensions | Extensions/second |
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

## Database Management

### Prerequisites
- Node.js >= 14.0.0
- npm (comes with Node.js)
- Python 3.x (for SQLite operations)

### Quick Start

1. Initialize the database environment:
```bash
npm run db:init
```

2. Choose your database implementation:

#### Option 1: SQLite (Default)
```bash
# Uses the default SQLite implementation
npm start
```

#### Option 2: PostgreSQL with Prisma
```bash
# Update your .env file with PostgreSQL credentials first
npm run db:migrate
```

### Available Database Commands

```bash
# Initialize database environment
npm run db:init

# Run database migrations (PostgreSQL)
npm run db:migrate

# Generate Prisma Client
npm run db:generate

# Open Prisma Studio (database GUI)
npm run db:studio

# Reset database (Caution: deletes all data)
npm run db:reset
```

### Database Tools

- **SQLite**: Uses built-in Python sqlite3 module
- **PostgreSQL**: Managed through Prisma with additional features:
  - Prisma Studio for GUI database management
  - Database migrations and versioning
  - Type-safe database client
  - Connection pooling and caching through Prisma Accelerate

For detailed setup instructions and configuration options, see the [Database Setup Guide](docs/database_setup.md).

### Security Notes
- Database credentials are stored in `.env` (never committed to version control)
- Regular database backups are recommended
- Use appropriate access controls for production deployments
- Follow security best practices outlined in the documentation

## Repository Organization

This repository has been reorganized to provide a clear structure based on extension categories. Each extension is placed in its respective category directory under `extensions/`:

- `extensions/cloud_devops/`: Cloud and DevOps related extensions
- `extensions/programming_languages/`: Language support and programming tools
- `extensions/remote_development/`: Remote development capabilities
- `extensions/ai_ml/`: AI and Machine Learning tools
- `extensions/development_tools/`: Development utilities
- `extensions/other/`: Additional extensions and utilities

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
│   ├── ai_ml/                # AI & Machine Learning extensions
│   ├── cloud_devops/         # Cloud & DevOps extensions
│   ├── development_tools/    # Development tools extensions
│   ├── other/                # Other miscellaneous extensions
│   ├── programming_languages/# Programming language extensions
│   └── remote_development/   # Remote development extensions
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
