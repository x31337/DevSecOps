# VS Code Insiders Extensions - Quick Reference

This quick reference card provides common commands and tips for working with the VS Code Insiders Extensions repository.

## Most Common Commands

### Installation Commands

```bash
# Fast parallel installation (recommended)
mpiexec -n 4 python3 scripts/parallel_install_extensions.py

# Standard sequential installation
./scripts/install_cursor_extensions.sh

# Install specific extensions
./scripts/install_cursor_extensions.sh --extensions github.copilot,ms-python.python

# Handle gzipped VSIX files
./scripts/install_gzipped_extensions.sh
```

### Extension Management

```bash
# Update VS Code engine version for all extensions
python3 scripts/update_vsix_engine.py

# Fix GitHub extensions specifically
python3 scripts/fix_github_extensions.py

# Generate database and documentation
python3 scripts/create_extension_db.py
```

## Installation Examples

### Basic Installation Scenarios

```bash
# Install all extensions in parallel with 4 processes
mpiexec -n 4 python3 scripts/parallel_install_extensions.py

# Install all extensions sequentially
./scripts/install_cursor_extensions.sh

# Install only specific extensions
./scripts/install_cursor_extensions.sh --extensions github.copilot,ms-python.python,ms-python.vscode-pylance

# Install from a different source directory
./scripts/install_cursor_extensions.sh --source ./extensions/new
mpiexec -n 4 python3 scripts/parallel_install_extensions.py --source ./extensions/new
```

### Advanced Installation Scenarios

```bash
# Install to a custom location
./scripts/install_cursor_extensions.sh --path ~/custom/cursor/location

# Parallel installation with 8 processes for very large extension sets
mpiexec -n 8 python3 scripts/parallel_install_extensions.py

# Force reinstallation of all extensions
./scripts/install_cursor_extensions.sh --force

# Skip backup of extensions.json
mpiexec -n 4 python3 scripts/parallel_install_extensions.py --skip-backup
```

## Key Operations with Extensions

### Updating VS Code Engine Version

```bash
# Update all extensions to be compatible with VS Code ^1.99.0
python3 scripts/update_vsix_engine.py

# Update specific extensions
python3 scripts/update_vsix_engine.py --extensions github.copilot,ms-python.python
```

### Working with Extension Database

```bash
# Generate or update extension inventory database
python3 scripts/create_extension_db.py

# Generate documentation based on extension database
python3 scripts/create_extension_db.py
```

### Managing Extensions in Cursor IDE

```bash
# Fix extensions.json file
python3 scripts/fix_extensions_json.py

# Fix GitHub-specific extensions
python3 scripts/fix_github_extensions.py
```

## Common Flags and Options

### Standard Installation Options

| Flag | Description | Example |
|------|-------------|---------|
| `--source` | Source directory with extensions | `--source ./extensions/new` |
| `--extensions` | Comma-separated list of extensions | `--extensions github.copilot,ms-python.python` |
| `--path` | Cursor IDE installation path | `--path ~/Applications/Cursor.AppImage` |
| `--force` | Force reinstallation | `--force` |
| `--yes` | Auto-confirm all prompts | `--yes` |

### Parallel Installation Options

| Flag | Description | Example |
|------|-------------|---------|
| `-n` | Number of MPI processes | `-n 4` |
| `--source` | Source directory | `--source ./extensions` |
| `--target` | Target directory | `--target ~/.cursor/extensions` |
| `--skip-backup` | Skip backing up extensions.json | `--skip-backup` |

## Performance Tips

1. **Use parallel installation** whenever possible. It's 4x faster with 4 cores.
   ```bash
   mpiexec -n 4 python3 scripts/parallel_install_extensions.py
   ```

2. **Match process count to available cores** for optimal performance.
   ```bash
   # For an 8-core system
   mpiexec -n 8 python3 scripts/parallel_install_extensions.py
   ```

3. **Reduce logging verbosity** for faster installation.
   ```bash
   # Standard installation with minimal output
   ./scripts/install_cursor_extensions.sh --quiet
   ```

4. **Group extensions by size** for more balanced parallel processing.
   ```bash
   # For extensions in specific categories
   mpiexec -n 4 python3 scripts/parallel_install_extensions.py --source ./extensions/new/ai
   mpiexec -n 4 python3 scripts/parallel_install_extensions.py --source ./extensions/new/languages
   ```

5. **Keep extensions organized** by category for easier management.
   ```bash
   # Create organized directory structure
   mkdir -p extensions/{languages,devops,ai,remote}
   
   # Install from specific category
   ./scripts/install_cursor_extensions.sh --source ./extensions/ai
   ```

