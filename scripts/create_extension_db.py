#!/usr/bin/env python3
import os
import re
import sys
import json
import sqlite3
import datetime
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Get the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Configuration with absolute paths for reliability
EXTENSIONS_DIR = os.path.join(PROJECT_ROOT, "extensions")
DB_DIR = os.path.join(PROJECT_ROOT, "db")
OUTPUT_DB = os.path.join(DB_DIR, "extension_inventory.db")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
README_TEMPLATE = os.path.join(PROJECT_ROOT, "README_template.md")
README_OUTPUT = os.path.join(PROJECT_ROOT, "README.md")

# Create necessary directories
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

# Extension categories with regex patterns for matching
CATEGORIES = {
    "Programming Languages": [
        r'vscode-python', r'python', r'pylance', r'typescript', r'javascript', r'csharp',
        r'java', r'go', r'rust', r'cpp', r'c-sharp', r'anycode', r'language-pack'
    ],
    "Remote Development": [
        r'remote-', r'remote\.', r'ssh', r'containers', r'wsl', r'remote-explorer'
    ],
    "Cloud & DevOps": [
        r'azure', r'aws', r'cloudcode', r'kubernetes', r'container', r'docker',
        r'github', r'devops', r'action', r'function', r'storage'
    ],
    "AI & Machine Learning": [
        r'copilot', r'chatgpt', r'openai', r'gemini', r'ai-', r'ml-', r'geminicodeassist'
    ],
    "Development Tools": [
        r'gitlens', r'debugpy', r'testing', r'debug', r'extension', r'extension-pack'
    ],
}

def setup_database(db_path: str) -> sqlite3.Connection:
    """Create database and tables if they don't exist."""
    # Ensure the database directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create extensions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS extensions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        publisher TEXT,
        name TEXT,
        display_name TEXT,
        version TEXT,
        description TEXT,
        category TEXT,
        size INTEGER,
        file_path TEXT,
        vscode_version TEXT,
        last_updated TEXT
    )
    ''')
    
    # Create categories table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        count INTEGER DEFAULT 0,
        total_size INTEGER DEFAULT 0
    )
    ''')
    
    conn.commit()
    return conn

def extract_extension_info(file_path: str) -> Dict:
    """Extract extension metadata from VSIX file."""
    basename = os.path.basename(file_path)
    size = os.path.getsize(file_path)
    
    # Default values
    info = {
        "publisher": "unknown",
        "name": "unknown",
        "display_name": basename,
        "version": "0.0.0",
        "description": "",
        "file_path": file_path,
        "size": size,
        "vscode_version": "^1.99.0",  # Default based on our updates
        "last_updated": datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
    }
    
    # Extract publisher and name from filename patterns
    # Pattern 1: publisher.extension@version.vsix
    match = re.match(r'^([^@\.]+)\.([^@\.]+)@(.+)\.vsix$', basename)
    if match:
        info["publisher"] = match.group(1)
        info["name"] = match.group(2)
        info["version"] = match.group(3)
        info["display_name"] = f"{match.group(1)}.{match.group(2)}"
        return info
    
    # Pattern 2: Publisher.extension-version.vsix
    match = re.match(r'^([^-\.]+)\.([^-\.]+)-([^-]+)(?:-(.+))?\.vsix$', basename)
    if match:
        info["publisher"] = match.group(1)
        info["name"] = match.group(2)
        info["version"] = match.group(3)
        info["display_name"] = f"{match.group(1)}.{match.group(2)}"
        return info
        
    # Try to extract more info from the package.json inside the VSIX
    # This is more complex and may require unzipping the VSIX
    # For simplicity, we'll skip this for now
    
    return info

def determine_category(extension_info: Dict) -> str:
    """Determine the category of an extension based on naming patterns."""
    full_name = f"{extension_info['publisher']}.{extension_info['name']}".lower()
    
    for category, patterns in CATEGORIES.items():
        for pattern in patterns:
            if re.search(pattern.lower(), full_name):
                return category
    
    return "Other"

def scan_extensions(directory: str) -> List[Dict]:
    """Scan for VSIX files and extract metadata."""
    extensions = []
    
    # Ensure directory exists
    if not os.path.exists(directory):
        print(f"Warning: Extensions directory not found: {directory}")
        return []
        
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.vsix'):
                file_path = os.path.join(root, file)
                print(f"Processing: {file_path}")
                
                info = extract_extension_info(file_path)
                info["category"] = determine_category(info)
                
                extensions.append(info)
    
    return extensions

def store_extensions(conn: sqlite3.Connection, extensions: List[Dict]) -> None:
    """Store extension data in the database."""
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM extensions")
    cursor.execute("DELETE FROM categories")
    
    # Insert extension data
    for ext in extensions:
        cursor.execute('''
        INSERT INTO extensions 
        (publisher, name, display_name, version, description, category, size, file_path, vscode_version, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ext["publisher"],
            ext["name"],
            ext["display_name"],
            ext["version"],
            ext.get("description", ""),
            ext["category"],
            ext["size"],
            ext["file_path"],
            ext.get("vscode_version", "^1.99.0"),
            ext["last_updated"]
        ))
    
    # Update category statistics
    cursor.execute('''
    INSERT INTO categories (name, count, total_size)
    SELECT category, COUNT(*), SUM(size)
    FROM extensions
    GROUP BY category
    ''')
    
    conn.commit()

def format_size(size_bytes: int) -> str:
    """Format size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def generate_docs(conn: sqlite3.Connection) -> None:
    """Generate documentation files."""
    cursor = conn.cursor()
    
    # Create docs directory if it doesn't exist
    os.makedirs(DOCS_DIR, exist_ok=True)
    
    # Generate index.md
    with open(os.path.join(DOCS_DIR, "index.md"), "w") as f:
        f.write("# VS Code Insiders Extensions Documentation\n\n")
        f.write("This documentation provides detailed information about the extensions in this repository.\n\n")
        f.write("## Contents\n\n")
        f.write("- [Extension Categories](categories.md)\n")
        f.write("- [Extensions by Size](extensions_by_size.md)\n")
        
        # Add category links
        cursor.execute("SELECT name FROM categories ORDER BY name")
        for row in cursor.fetchall():
            category = row[0]
            filename = f"category_{category.lower().replace(' ', '_')}.md"
            f.write(f"- [{category}]({filename})\n")
    
    # Generate categories.md
    with open(os.path.join(DOCS_DIR, "categories.md"), "w") as f:
        f.write("# Extension Categories\n\n")
        f.write("| Category | Count | Total Size |\n")
        f.write("|----------|-------|------------|\n")
        
        cursor.execute("SELECT name, count, total_size FROM categories ORDER BY count DESC")
        for row in cursor.fetchall():
            category, count, size = row
            f.write(f"| [{category}](category_{category.lower().replace(' ', '_')}.md) | {count} | {format_size(size)} |\n")
    
    # Generate extensions_by_size.md
    with open(os.path.join(DOCS_DIR, "extensions_by_size.md"), "w") as f:
        f.write("# Extensions by Size\n\n")
        f.write("| Extension | Version | Size | Category |\n")
        f.write("|-----------|---------|------|----------|\n")
        
        cursor.execute("SELECT display_name, version, size, category FROM extensions ORDER BY size DESC")
        for row in cursor.fetchall():
            name, version, size, category = row
            f.write(f"| {name} | {version} | {format_size(size)} | {category} |\n")
    
    # Generate category files
    cursor.execute("SELECT DISTINCT category FROM extensions ORDER BY category")
    for row in cursor.fetchall():
        category = row[0]
        filename = f"category_{category.lower().replace(' ', '_')}.md"
        
        with open(os.path.join(DOCS_DIR, filename), "w") as f:
            f.write(f"# {category} Extensions\n\n")
            f.write("| Extension | Version | Size | Description |\n")
            f.write("|-----------|---------|------|-------------|\n")
            
            cursor.execute('''
            SELECT display_name, version, size, description 
            FROM extensions 
            WHERE category = ? 
            ORDER BY display_name
            ''', (category,))
            
            for ext_row in cursor.fetchall():
                name, version, size, description = ext_row
                f.write(f"| {name} | {version} | {format_size(size)} | {description[:50]}{'...' if len(description) > 50 else ''} |\n")

def update_readme(conn: sqlite3.Connection) -> None:
    """Update the README.md file with summary information."""
    cursor = conn.cursor()
    
    # Get total counts
    cursor.execute("SELECT COUNT(*), SUM(size) FROM extensions")
    total_extensions, total_size = cursor.fetchone()
    
    # Get category counts
    categories = []
    cursor.execute("SELECT name, count FROM categories ORDER BY count DESC")
    for row in cursor.fetchall():
        categories.append(f"* {row[0]}: {row[1]} extensions")
    
    # Create a new README from template if it exists, otherwise create from scratch
    if os.path.exists(README_TEMPLATE):
        with open(README_TEMPLATE, "r") as template:
            content = template.read()
            
        # Replace placeholders
        content = content.replace("{{TOTAL_EXTENSIONS}}", str(total_extensions))
        content = content.replace("{{TOTAL_SIZE}}", format_size(total_size))
        content = content.replace("{{CATEGORIES}}", "\n".join(categories))
        
        with open(README_OUTPUT, "w") as output:
            output.write(content)
    else:
        # Create a basic README
        with open(README_OUTPUT, "w") as f:
            f.write("# VS Code Insiders Extensions Collection\n\n")
            f.write("A comprehensive collection of VS Code Insiders extensions with installation scripts for VS Code and Cursor IDE.\n\n")
            
            f.write("## Extension Overview\n")
            f.write(f"* Total number of extensions: {total_extensions}\n")
            f.write(f"* Total size of all extensions: {format_size(total_size)}\n\n")
            
            f.write("### Categories\n")
            for category in categories:
                f.write(f"{category}\n")
            
            f.write("\n[See detailed category breakdown](docs/categories.md)\n\n")
            
            f.write("## Installation Instructions\n\n")
            f.write("### Prerequisites\n")
            f.write("- Git with LFS support (for cloning this repository)\n")
            f.write("- VS Code or Cursor IDE\n")
            f.write("- Bash shell environment\n")
            f.write("- `unzip` utility (for extension installation)\n\n")
            
            f.write("### Installing Extensions in Cursor IDE\n\n")
            f.write("```bash\n")
            f.write("# Run the installation script with default options\n")
            f.write("./scripts/install_cursor_extensions.sh\n")
            f.write("```\n\n")
            
            f.write("[See detailed installation instructions](docs/index.md)\n\n")
            
            f.write("## Available Scripts\n\n")
            f.write("* `install_cursor_extensions.sh` - Comprehensive installation script for Cursor IDE\n")
            f.write("* `install_gzipped_extensions.sh` - Special script for handling gzipped VSIX files\n")
            f.write("* `update_vsix_engine.py` - Updates VS Code engine versions in VSIX packages\n")
            f.write("* `fix_github_extensions.py` - Fixes GitHub extension compatibility issues\n")
            f.write("* `create_extension_db.py` - Creates extension inventory database and documentation\n\n")
            
            f.write("[See detailed script documentation](docs/index.md)\n")

def main() -> None:
    """Main function to process extensions and generate documentation."""
    print(f"Starting extension inventory creation at {datetime.datetime.now()}")
    
    # Log configuration
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Extensions directory: {EXTENSIONS_DIR}")
    print(f"Database directory: {DB_DIR}")
    print(f"Documentation directory: {DOCS_DIR}")
    
    # Setup database
    print(f"Setting up database at {OUTPUT_DB}")
    conn = setup_database(OUTPUT_DB)
    
    # Scan for extensions
    print(f"Scanning for extensions in {EXTENSIONS_DIR}")
    extensions = scan_extensions(EXTENSIONS_DIR)
    print(f"Found {len(extensions)} extensions")
    
    # Store in database
    print("Storing extension data in database")
    store_extensions(conn, extensions)
    
    # Generate documentation
    print(f"Generating documentation in {DOCS_DIR}")
    generate_docs(conn)
    
    # Update README
    print(f"Updating README at {README_OUTPUT}")
    update_readme(conn)
    
    # Close database connection
    conn.close()
    
    print(f"Extension inventory creation completed at {datetime.datetime.now()}")
    print(f"- Database: {OUTPUT_DB}")
    print(f"- Documentation: {DOCS_DIR}")
    print(f"- README: {README_OUTPUT}")

if __name__ == "__main__":
    main()

