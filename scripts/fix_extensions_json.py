#!/usr/bin/env python3
import os
import json
import re
from pathlib import Path

def normalize_extension_info(dirname):
    # Special handling for known patterns
    if 'vscode-codeql' in dirname:
        match = re.match(r'(GitHub)\.vscode-codeql-([^-]+)(?:-(.+))?', dirname)
        if match:
            publisher, version, extra = match.groups()
            return publisher, 'vscode-codeql', version
            
    if 'vscode-github-actions' in dirname:
        match = re.match(r'(GitHub)\.vscode-github-actions-([^-]+)(?:-(.+))?', dirname)
        if match:
            publisher, version, extra = match.groups()
            return publisher, 'vscode-github-actions', version
            
    if 'vscode-pull-request-github' in dirname:
        match = re.match(r'(GitHub)\.vscode-pull-request-github-([^-]+)(?:-(.+))?', dirname)
        if match:
            publisher, version, extra = match.groups()
            return publisher, 'vscode-pull-request-github', version
    
    # Standard pattern for other extensions
    parts = dirname.rsplit('-', 1)
    if len(parts) != 2:
        return None
        
    base_name, version = parts
    publisher_parts = base_name.split('.', 1)
    if len(publisher_parts) != 2:
        return None
        
    publisher, extension_name = publisher_parts
    return publisher, extension_name, version

def main():
    extensions_dir = os.path.expanduser("~/.cursor/extensions")
    extensions = []
    processed = 0
    skipped = 0
    seen_extensions = set()  # Track unique extension IDs
    
    # First pass: collect all directories and their normalized info
    ext_info = []
    for entry in os.scandir(extensions_dir):
        if not entry.is_dir():
            continue
            
        if entry.name.startswith('.') or '-linux-x64' in entry.name:
            skipped += 1
            continue
            
        result = normalize_extension_info(entry.name)
        if not result:
            print(f"Skipping directory with unexpected format: {entry.name}")
            skipped += 1
            continue
            
        publisher, extension_name, version = result
        ext_id = f"{publisher}.{extension_name}"
        
        # For duplicate IDs, keep only the latest version
        if ext_id in seen_extensions:
            continue
            
        seen_extensions.add(ext_id)
        
        ext_entry = {
            "identifier": {
                "id": ext_id
            },
            "version": version,
            "location": {
                "$mid": 1,
                "path": str(Path(entry.path)),
                "scheme": "file"
            },
            "relativeLocation": entry.name
        }
        
        extensions.append(ext_entry)
        processed += 1
        
    # Sort extensions by identifier
    extensions.sort(key=lambda x: x["identifier"]["id"].lower())
    
    # Write the new extensions.json
    extensions_json_path = os.path.join(extensions_dir, "extensions.json")
    
    # Backup existing file
    if os.path.exists(extensions_json_path):
        with open(extensions_json_path, 'r') as f:
            content = f.read().strip()
            if content and content != "[]":
                backup_path = f"{extensions_json_path}.backup.{os.path.getmtime(extensions_json_path):.0f}"
                os.rename(extensions_json_path, backup_path)
                print(f"Backed up existing extensions.json to {os.path.basename(backup_path)}")
    
    # Write new file
    with open(extensions_json_path, 'w') as f:
        json.dump(extensions, f, indent=2)
    
    print(f"\nExtensions processed: {processed}")
    print(f"Entries skipped: {skipped}")
    print(f"New extensions.json written with {len(extensions)} entries")
    
    print("\nSample of processed extensions:")
    for ext in extensions[:5]:
        print(f"- {ext['identifier']['id']} v{ext['version']}")

if __name__ == "__main__":
    main()
