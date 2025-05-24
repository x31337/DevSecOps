#!/usr/bin/env python3
import os
import sys
import json
import zipfile
import sqlite3
import tempfile
import logging
import datetime
import re
from pathlib import Path
import shutil
import hashlib
import gzip
from typing import Dict, List, Tuple, Optional, Any

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(log_dir, exist_ok=True)

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"extension_inventory_{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

# Database constants
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "extension_inventory.db")
DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
EXTENSIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "extensions")

# Known categories for extensions
CATEGORIES = {
    "development": {
        "id": 1,
        "name": "Development Tools",
        "description": "General development tools and extensions",
        "keywords": ["development", "tool", "utility", "edit", "developer"]
    },
    "programming": {
        "id": 2,
        "name": "Programming Languages",
        "description": "Language support and programming tools",
        "keywords": ["language", "programming", "code", "syntax"]
    },
    "cloud": {
        "id": 3,
        "name": "Cloud & DevOps",
        "description": "Cloud services and DevOps tools",
        "keywords": ["cloud", "azure", "aws", "google", "devops", "kubernetes", "docker", "container"]
    },
    "ai": {
        "id": 4,
        "name": "AI & Machine Learning",
        "description": "AI, ML, and coding assistance tools",
        "keywords": ["ai", "machine learning", "ml", "copilot", "codex", "assistant", "gpt"]
    },
    "remote": {
        "id": 5,
        "name": "Remote Development",
        "description": "Remote development and collaboration tools",
        "keywords": ["remote", "ssh", "wsl", "container", "collaborate"]
    },
    "theme": {
        "id": 6,
        "name": "Themes & UI",
        "description": "Visual themes and UI enhancements",
        "keywords": ["theme", "color", "icon", "ui", "interface"]
    },
    "other": {
        "id": 99,
        "name": "Other",
        "description": "Miscellaneous extensions",
        "keywords": []
    }
}

# Extension name to category mapping for known extensions
KNOWN_EXTENSIONS = {
    "ms-python.python": "programming",
    "ms-python.vscode-pylance": "programming",
    "github.copilot": "ai",
    "github.copilot-chat": "ai",
    "ms-vscode-remote.remote-ssh": "remote",
    "ms-vscode-remote.remote-containers": "remote",
    "ms-vscode-remote.remote-wsl": "remote",
    "ms-azuretools.vscode-docker": "cloud",
    "ms-kubernetes-tools.vscode-kubernetes-tools": "cloud",
    "ms-dotnettools.csharp": "programming",
    "redhat.java": "programming",
    "dbaeumer.vscode-eslint": "programming",
    "ms-vscode.powershell": "programming",
    "googlecloudtools.cloudcode": "cloud",
    "google.geminicodeassist": "ai",
    "ms-azuretools.vscode-azure-github-copilot": "ai",
    "ms-vsliveshare.vsliveshare": "remote",
    "GitHub.vscode-pull-request-github": "development",
    "eamodio.gitlens": "development",
    "vscode.github": "development"
}

def create_database() -> None:
    """Create the SQLite database with the required schema."""
    logging.info("Creating database schema...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create categories table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT
    )
    ''')
    
    # Create extensions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS extensions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        publisher TEXT,
        version TEXT,
        display_name TEXT,
        description TEXT,
        size INTEGER,
        category_id INTEGER,
        file_name TEXT,
        metadata TEXT,
        FOREIGN KEY (category_id) REFERENCES categories (id)
    )
    ''')
    
    # Populate categories
    cursor.execute('DELETE FROM categories')
    for cat_info in CATEGORIES.values():
        cursor.execute(
            'INSERT INTO categories (id, name, description) VALUES (?, ?, ?)',
            (cat_info["id"], cat_info["name"], cat_info["description"])
        )
    
    conn.commit()
    conn.close()
    logging.info("Database schema created successfully")

def find_package_json(directory: str) -> Optional[str]:
    """Find package.json file in the extracted directory structure."""
    for root, _, files in os.walk(directory):
        if "package.json" in files:
            return os.path.join(root, "package.json")
    return None

def extract_vsix_metadata(vsix_path: str) -> Dict[str, Any]:
    """Extract metadata from a VSIX file (handles both ZIP and GZIP formats)."""
    metadata = {
        "name": None,
        "publisher": None,
        "version": None,
        "display_name": None,
        "description": None,
        "categories": [],
        "keywords": [],
        "engines": {}
    }
    
    file_name = os.path.basename(vsix_path)
    file_size = os.path.getsize(vsix_path)
    
    # Extract info from filename
    name_parts = re.match(r'([^@-]+)[.-]([^@-]+)[@-](.+)\.vsix', file_name)
    if name_parts:
        metadata["publisher"] = name_parts.group(1)
        metadata["name"] = name_parts.group(2)
        metadata["version"] = name_parts.group(3)
    
    # Create a temporary directory for extraction
    temp_dir = tempfile.mkdtemp(prefix="vsix_extract_")
    temp_zip_path = os.path.join(temp_dir, "extracted.zip")
    
    try:
        extraction_successful = False
        
        # Method 1: Try to handle as a gzipped file first
        try:
            logging.debug(f"Attempting to extract {file_name} as a GZIP file")
            with gzip.open(vsix_path, 'rb') as f_in:
                with open(temp_zip_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Now try to open the extracted content as a ZIP file
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                extraction_successful = True
                logging.debug(f"Successfully extracted {file_name} as a GZIP+ZIP file")
        except (gzip.BadGzipFile, zipfile.BadZipFile, OSError) as e:
            logging.debug(f"GZIP extraction failed for {file_name}: {str(e)}")
            # If the gzip method failed, we'll try the direct ZIP method next
        
        # Method 2: Try direct ZIP extraction if GZIP method failed
        if not extraction_successful:
            try:
                logging.debug(f"Attempting to extract {file_name} as a direct ZIP file")
                with zipfile.ZipFile(vsix_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                    extraction_successful = True
                    logging.debug(f"Successfully extracted {file_name} as a direct ZIP file")
            except zipfile.BadZipFile:
                logging.warning(f"Could not extract {file_name} as either GZIP or ZIP file")
        
        # If extraction failed through both methods, return basic metadata
        if not extraction_successful:
            return {**metadata, "file_name": file_name, "size": file_size}
        
        # Look for package.json
        package_json_path = find_package_json(temp_dir)
        if package_json_path:
            try:
                with open(package_json_path, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                
                # Update metadata with package.json information
                metadata["name"] = package_data.get("name", metadata["name"])
                metadata["publisher"] = package_data.get("publisher", metadata["publisher"])
                metadata["version"] = package_data.get("version", metadata["version"])
                metadata["display_name"] = package_data.get("displayName", metadata["display_name"])
                metadata["description"] = package_data.get("description", metadata["description"])
                metadata["categories"] = package_data.get("categories", [])
                metadata["keywords"] = package_data.get("keywords", [])
                metadata["engines"] = package_data.get("engines", {})
            except Exception as e:
                logging.error(f"Error parsing package.json for {file_name}: {e}")
        
        # Look for extension.vsixmanifest
        vsixmanifest_path = os.path.join(temp_dir, "extension.vsixmanifest")
        if os.path.exists(vsixmanifest_path):
            try:
                with open(vsixmanifest_path, 'r', encoding='utf-8') as f:
                    manifest_content = f.read()
                
                # Extract Identity attributes
                identity_match = re.search(r'<Identity[^>]*Id="([^"]+)"[^>]*Version="([^"]+)"[^>]*Publisher="([^"]+)"', manifest_content)
                if identity_match:
                    full_id = identity_match.group(1)
                    version = identity_match.group(2)
                    publisher = identity_match.group(3)
                    
                    # Split the full ID if it contains a publisher
                    if "." in full_id:
                        id_parts = full_id.split(".", 1)
                        if len(id_parts) == 2:
                            if not metadata["publisher"]:
                                metadata["publisher"] = id_parts[0]
                            metadata["name"] = id_parts[1]
                    else:
                        metadata["name"] = full_id
                    
                    if not metadata["publisher"]:
                        metadata["publisher"] = publisher
                    if not metadata["version"]:
                        metadata["version"] = version
                
                # Extract DisplayName
                display_name_match = re.search(r'<DisplayName>(.*?)</DisplayName>', manifest_content)
                if display_name_match and not metadata["display_name"]:
                    metadata["display_name"] = display_name_match.group(1)
                
                # Extract Description
                description_match = re.search(r'<Description>(.*?)</Description>', manifest_content)
                if description_match and not metadata["description"]:
                    metadata["description"] = description_match.group(1)
            except Exception as e:
                logging.error(f"Error parsing vsixmanifest for {file_name}: {e}")
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    return {**metadata, "file_name": file_name, "size": file_size}

def determine_category(metadata: Dict[str, Any]) -> int:
    """Determine the category ID for an extension based on its metadata."""
    extension_id = f"{metadata['publisher']}.{metadata['name']}" if metadata['publisher'] and metadata['name'] else metadata['name']
    
    # Check known extensions mapping first
    if extension_id in KNOWN_EXTENSIONS:
        return CATEGORIES[KNOWN_EXTENSIONS[extension_id]]["id"]
    
    # Check categories list in metadata
    if metadata["categories"]:
        for category in metadata["categories"]:
            category_lower = category.lower()
            if "theme" in category_lower:
                return CATEGORIES["theme"]["id"]
            elif "language" in category_lower:
                return CATEGORIES["programming"]["id"]
            elif any(cloud_term in category_lower for cloud_term in ["cloud", "azure", "aws"]):
                return CATEGORIES["cloud"]["id"]
        
    # Check keywords
    all_text = " ".join([
        metadata.get("display_name", "") or "",
        metadata.get("description", "") or "",
        " ".join(metadata.get("keywords", []))
    ]).lower()
    
    # Check each category's keywords
    for cat_key, cat_info in CATEGORIES.items():
        if cat_key == "other":
            continue
        
        for keyword in cat_info["keywords"]:
            if keyword.lower() in all_text:
                return cat_info["id"]
    
    # Default to Other
    return CATEGORIES["other"]["id"]

def scan_extensions() -> List[Dict[str, Any]]:
    """Scan the extensions directory and extract metadata."""
    logging.info("Scanning extensions directory...")
    extensions_data = []
    
    vsix_files = [f for f in os.listdir(EXTENSIONS_DIR) if f.endswith('.vsix')]
    total_files = len(vsix_files)
    logging.info(f"Found {total_files} VSIX files")
    
    for i, filename in enumerate(vsix_files, 1):
        try:
            vsix_path = os.path.join(EXTENSIONS_DIR, filename)
            logging.info(f"Processing [{i}/{total_files}]: {filename}")
            
            metadata = extract_vsix_metadata(vsix_path)
            category_id = determine_category(metadata)
            
            extension_data = {
                "name": metadata["name"],
                "publisher": metadata["publisher"],
                "version": metadata["version"],
                "display_name": metadata["display_name"],
                "description": metadata["description"],
                "size": metadata["size"],
                "category_id": category_id,
                "file_name": metadata["file_name"],
                "metadata": json.dumps(metadata)
            }
            
            extensions_data.append(extension_data)
            
        except Exception as e:
            logging.error(f"Error processing {filename}: {e}")
    
    return extensions_data

def populate_database(extensions_data: List[Dict[str, Any]]) -> None:
    """Populate the database with extension data."""
    logging.info("Populating database with extension data...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute('DELETE FROM extensions')
    
    # Insert extension data
    for ext in extensions_data:
        cursor.execute('''
        INSERT INTO extensions 
        (name, publisher, version, display_name, description, size, category_id, file_name, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ext["name"],
            ext["publisher"],
            ext["version"],
            ext["display_name"],
            ext["description"],
            ext["size"],
            ext["category_id"],
            ext["file_name"],
            ext["metadata"]
        ))
    
    conn.commit()
    conn.close()
    logging.info(f"Database populated with {len(extensions_data)} extensions")

def format_size(size_bytes: int) -> str:
    """Format size in bytes to human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def generate_markdown_docs() -> None:
    """Generate markdown documentation from the database."""
    logging.info("Generating markdown documentation...")
    os.makedirs(DOCS_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get category information
    cursor.execute('SELECT * FROM categories ORDER BY id')
    categories = {row['id']: dict(row) for row in cursor.fetchall()}
    
    # Get extension counts and sizes by category
    cursor.execute('''
    SELECT category_id, COUNT(*) as count, SUM(size) as total_size
    FROM extensions
    GROUP BY category_id
    ''')
    category_stats = {row['category_id']: dict(row) for row in cursor.fetchall()}
    
    # Get all extensions
    cursor.execute('''
    SELECT e.*, c.name as category_name
    FROM extensions e
    JOIN categories c ON e.category_id = c.id
    ORDER BY e.name
    ''')
    all_extensions = [dict(row) for row in cursor.fetchall()]
    
    # 1. Generate category overview
    with open(os.path.join(DOCS_DIR, "categories.md"), 'w') as f:
        f.write("# Extension Categories\n\n")
        
        f.write("| Category | Count | Total Size | Description |\n")
        f.write("|----------|-------|------------|-------------|\n")
        
        total_count = sum(stats['count'] for stats in category_stats.values())
        total_size = sum(stats['total_size'] for stats in category_stats.values())
        
        for cat_id, cat_info in categories.items():
            stats = category_stats.get(cat_id, {'count': 0, 'total_size': 0})
            f.write(f"| [{cat_info['name']}](category_{cat_id}.md) | {stats['count']} | {format_size(stats['total_size'])} | {cat_info['description']} |\n")
        
        f.write(f"\n**Total: {total_count} extensions, {format_size(total_size)}**\n")
    
    # 2. Generate individual category pages
    for cat_id, cat_info in categories.items():
        cursor.execute('''
        SELECT e.*, c.name as category_name
        FROM extensions e
        JOIN categories c ON e.category_id = c.id
        WHERE e.category_id = ?
        ORDER BY e.name
        ''', (cat_id,))
        
        cat_extensions = [dict(row) for row in cursor.fetchall()]
        
        if not cat_extensions:
            continue
        
        with open(os.path.join(DOCS_DIR, f"category_{cat_id}.md"), 'w') as f:
            f.write(f"# {cat_info['name']} Extensions\n\n")
            f.write(f"{cat_info['description']}\n\n")
            
            f.write("| Extension | Publisher | Version | Size | Description |\n")
            f.write("|-----------|-----------|---------|------|-------------|\n")
            
            for ext in cat_extensions:
                display_name = ext['display_name'] or ext['name']
                description = (ext['description'] or "")[:100] + ("..." if ext['description'] and len(ext['description']) > 100 else "")
                f.write(f"| {display_name} | {ext['publisher'] or 'Unknown'} | {ext['version'] or 'Unknown'} | {format_size(ext['size'])} | {description} |\n")
    
    # 3. Generate extension list by size
    with open(os.path.join(DOCS_DIR, "extensions_by_size.md"), 'w') as f:
        f.write("# Extensions by Size\n\n")
        
        # Sort by size (largest first)
        sorted_by_size = sorted(all_extensions, key=lambda x: x['size'], reverse=True)
        
        f.write("## Largest Extensions\n\n")
        f.write("| Extension | Publisher | Size | Category |\n")
        f.write("|-----------|-----------|------|----------|\n")
        
        for ext in sorted_by_size[:10]:
            display_name = ext['display_name'] or ext['name']
            f.write(f"| {display_name} | {ext['publisher'] or 'Unknown'} | {format_size(ext['size'])} | {ext['category_name']} |\n")
        
        f.write("\n## Smallest Extensions\n\n")
        f.write("| Extension | Publisher | Size | Category |\n")
        f.write("|-----------|-----------|------|----------|\n")
        
        for ext in sorted_by_size[-10:]:
            display_name = ext['display_name'] or ext['name']
            f.write(f"| {display_name} | {ext['publisher'] or 'Unknown'} | {format_size(ext['size'])} | {ext['category_name']} |\n")
    
    # 4. Generate main index
    with open(os.path.join(DOCS_DIR, "index.md"), 'w') as f:
        f.write("# VS Code Extensions Documentation\n\n")
        f.write("This documentation provides an overview of all the VS Code extensions in this repository.\n\n")
        
        total_count = sum(stats['count'] for stats in category_stats.values())
        total_size = sum(stats['total_size'] for stats in category_stats.values())
        
        f.write(f"**Total: {total_count} extensions, {format_size(total_size)}**\n\n")
        
        f.write("## Documentation Sections\n\n")
        f.write("* [Extension Categories](categories.md)\n")
        f.write("* [Extensions by Size](extensions_by_size.md)\n")
        
        f.write("\n## Category Pages\n\n")
        for cat_id, cat_info in categories.items():
            stats = category_stats.get(cat_id, {'count': 0, 'total_size': 0})
            if stats['count'] > 0:
                f.write(f"* [{cat_info['name']}](category_{cat_id}.md) ({stats['count']} extensions)\n")
    
    conn.close()
    logging.info("Markdown documentation generated successfully")

def update_readme() -> None:
    """Update the main README.md file to be more concise with references to docs."""
    logging.info("Updating README.md...")
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get extension counts and total size
    cursor.execute('SELECT COUNT(*) as count, SUM(size) as total_size FROM extensions')
    stats = dict(cursor.fetchone())
    
    # Get category counts
    cursor.execute('''
    SELECT c.name, COUNT(*) as count
    FROM extensions e
    JOIN categories c ON e.category_id = c.id
    GROUP BY e.category_id
    ORDER BY count DESC
    ''')
    categories = [dict(row) for row in cursor.fetchall()]
    
    # Get top extensions by size
    cursor.execute('''
    SELECT name, publisher, display_name, size
    FROM extensions
    ORDER BY size DESC
    LIMIT 5
    ''')
    largest_extensions = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # Read current README.md
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "README.md"), 'r') as f:
        readme_content = f.read()
    
    # Keep the first part (up to Repository Structure)
    sections = readme_content.split("## Repository Structure")
    header = sections[0]
    
    # Create new content
    new_content = header + "## Repository Structure\n\n"
    new_content += "```\n"
    new_content += ".\n"
    new_content += "├── README.md                 # This file\n"
    new_content += "├── LICENSE                   # License information\n"
    new_content += "├── docs/                     # Detailed documentation\n"
    new_content += "│   ├── index.md              # Documentation index\n"
    new_content += "│   ├── categories.md         # Extension categories\n"
    new_content += "│   ├── extensions_by_size.md # Extensions sorted by size\n"
    new_content += "│   └── category_*.md         # Category-specific documentation\n"
    new_content += "├── extension_inventory.db    # Extension metadata database\n"
    new_content += "├── extensions/               # Directory containing all .vsix extension files\n"
    new_content += "├── logs/                     # Installation logs and extension lists\n"
    new_content += "│   ├── cursor_extension_install_*.log   # Installation logs\n"
    new_content += "│   ├── extensions_with_versions.txt     # List of extensions with versions\n"
    new_content += "│   └── failed_downloads.txt             # Any failed download attempts\n"
    new_content += "└── scripts/                  # Installation and utility scripts\n"
    new_content += "    ├── create_extension_db.py          # Script to create extension inventory\n"
    new_content += "    ├── download_extensions.sh          # Script to download extensions\n"
    new_content += "    ├── fix_extensions_json.py          # Script to fix and normalize extensions.json\n"
    new_content += "    ├── fix_github_extensions.py        # Script to fix GitHub extension compatibility\n"
    new_content += "    ├── install_cursor_extensions.sh    # Comprehensive Cursor IDE installation script\n"
    new_content += "    └── update_vsix_engine.py           # Script to update VSIX engine versions\n"
    new_content += "```\n\n"
    
    # Extension Overview
    new_content += "## Extension Overview\n"
    new_content += f"* Total number of extensions: {stats['count']}\n"
    new_content += f"* Total size of all extensions: {format_size(stats['total_size'])}\n\n"
    
    # Add category summary
    new_content += "### Categories\n"
    for category in categories:
        new_content += f"* {category['name']}: {category['count']} extensions\n"
    new_content += "\n[See detailed category breakdown](docs/categories.md)\n\n"
    
    # Add installation instructions section
    new_content += "## Installation Instructions\n\n"
    new_content += "### Prerequisites\n"
    new_content += "- Git with LFS support (for cloning this repository)\n"
    new_content += "- VS Code or Cursor IDE\n"
    new_content += "- Bash shell environment\n"
    new_content += "- `unzip` utility (for extension installation)\n\n"
    
    new_content += "### Installing Extensions in Cursor IDE\n\n"
    new_content += "```bash\n"
    new_content += "# Run the installation script with default options\n"
    new_content += "./scripts/install_cursor_extensions.sh\n"
    new_content += "```\n\n"
    
    new_content += "[See detailed installation instructions](docs/index.md)\n\n"
    
    # Add scripts overview
    new_content += "## Available Scripts\n\n"
    new_content += "* `install_cursor_extensions.sh` - Comprehensive installation script for Cursor IDE\n"
    new_content += "* `download_extensions.sh` - Downloads VS Code extensions from the marketplace\n"
    new_content += "* `create_extension_db.py` - Creates extension inventory database and documentation\n"
    new_content += "* `fix_extensions_json.py` - Fixes and normalizes extensions.json files\n"
    new_content += "* `fix_github_extensions.py` - Fixes GitHub extension compatibility issues\n"
    new_content += "* `update_vsix_engine.py` - Updates VS Code engine versions in VSIX packages\n\n"
    
    new_content += "[See detailed script documentation](docs/index.md)\n\n"
    
    # Write updated README
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "README.md"), 'w') as f:
        f.write(new_content)
    
    logging.info("README.md updated successfully")

def main() -> None:
    """Main function to orchestrate the process."""
    logging.info("Starting extension inventory creation...")
    
    # Create directories if they don't exist
    os.makedirs(DOCS_DIR, exist_ok=True)
    
    # Step 1: Create database schema
    create_database()
    
    # Step 2: Scan extensions and extract metadata
    extensions_data = scan_extensions()
    
    # Step 3: Populate the database
    populate_database(extensions_data)
    
    # Step 4: Generate markdown documentation
    generate_markdown_docs()
    
    # Step 5: Update README.md
    update_readme()
    
    logging.info("Extension inventory creation completed successfully")
    logging.info(f"Database file: {DB_FILE}")
    logging.info(f"Documentation: {DOCS_DIR}")
    logging.info(f"Log file: {log_file}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
        sys.exit(1)

