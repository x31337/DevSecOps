#!/usr/bin/env python3
"""
Configuration Version Management Tool

This script provides functionality to manage, version, and track changes
to configuration files. It allows saving versions, listing history,
comparing versions, rolling back to previous states, and now includes
validation and tagging capabilities.
"""

import os
import sys
import json
import yaml
import shutil
import logging
import argparse
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
import hashlib
import difflib
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ConfigManager:
    """Manages configuration versions and history."""
    
    def __init__(self, config_file='config/export_config.yaml', versions_dir='config/versions'):
        """Initialize the configuration manager.
        
        Args:
            config_file: Path to the configuration file
            versions_dir: Directory to store version history
        """
        self.config_file = config_file
        self.versions_dir = versions_dir
        self.ensure_directories_exist()
    
    def ensure_directories_exist(self):
        """Ensure required directories exist."""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        os.makedirs(self.versions_dir, exist_ok=True)
    
    def load_config(self) -> Dict:
        """Load configuration from file."""
        if not os.path.exists(self.config_file):
            logging.warning(f"Configuration file {self.config_file} not found")
            return {}
        
        try:
            with open(self.config_file, 'r') as f:
                if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                    return yaml.safe_load(f) or {}
                elif self.config_file.endswith('.json'):
                    return json.load(f)
                else:
                    logging.error(f"Unsupported file format: {self.config_file}")
                    return {}
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            return {}
    
    def save_config(self, config: Dict) -> bool:
        """Save configuration to file.
        
        Args:
            config: Configuration data to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.config_file, 'w') as f:
                if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                    yaml.dump(config, f, default_flow_style=False)
                elif self.config_file.endswith('.json'):
                    json.dump(config, f, indent=2)
                else:
                    logging.error(f"Unsupported file format: {self.config_file}")
                    return False
            return True
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
            return False
    
    def generate_version_id(self, config: Dict) -> str:
        """Generate a unique version ID based on content and timestamp.
        
        Args:
            config: Configuration data
            
        Returns:
            str: Unique version ID
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        content_hash = hashlib.md5(json.dumps(config, sort_keys=True).encode()).hexdigest()[:8]
        return f"{timestamp}_{content_hash}"
    
    def save_version(self, message: str = "") -> Optional[str]:
        """Save current configuration as a new version.
        
        Args:
            message: Optional message describing the version
            
        Returns:
            Optional[str]: Version ID if successful, None otherwise
        """
        config = self.load_config()
        if not config:
            logging.error("Cannot save version: failed to load configuration")
            return None
        
        version_id = self.generate_version_id(config)
        version_file = os.path.join(self.versions_dir, f"{version_id}.json")
        
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'version_id': version_id,
            'message': message
        }
        
        version_data = {
            'metadata': metadata,
            'config': config
        }
        
        try:
            with open(version_file, 'w') as f:
                json.dump(version_data, f, indent=2)
            logging.info(f"Saved version {version_id}")
            return version_id
        except Exception as e:
            logging.error(f"Error saving version: {e}")
            return None
    
    def list_versions(self) -> List[Dict]:
        """List all saved configuration versions.
        
        Returns:
            List[Dict]: List of version metadata
        """
        versions = []
        
        for file_name in os.listdir(self.versions_dir):
            if file_name.endswith('.json') and not file_name == 'tags.json':
                file_path = os.path.join(self.versions_dir, file_name)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        if 'metadata' in data:
                            versions.append(data['metadata'])
                except Exception as e:
                    logging.warning(f"Error reading version file {file_name}: {e}")
        
        # Sort by timestamp (newest first)
        versions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return versions
    
    def show_version(self, version_id: str) -> Optional[Dict]:
        """Show details of a specific version.
        
        Args:
            version_id: ID of the version to show
            
        Returns:
            Optional[Dict]: Version data if found, None otherwise
        """
        version_file = os.path.join(self.versions_dir, f"{version_id}.json")
        if not os.path.exists(version_file):
            logging.error(f"Version {version_id} not found")
            return None
        
        try:
            with open(version_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading version {version_id}: {e}")
            return None
    
    def rollback(self, version_id: str) -> bool:
        """Roll back to a specific version.
        
        Args:
            version_id: ID of the version to roll back to
            
        Returns:
            bool: True if successful, False otherwise
        """
        version_data = self.show_version(version_id)
        if not version_data:
            return False
        
        # Backup current configuration
        backup_id = self.save_version("Automatic backup before rollback")
        if not backup_id:
            logging.warning("Failed to create backup before rollback")
        else:
            logging.info(f"Created backup with ID {backup_id}")
        
        # Apply rollback
        if self.save_config(version_data['config']):
            logging.info(f"Rolled back to version {version_id}")
            return True
        return False
    
    def compare_versions(self, version_id1: str, version_id2: str) -> Dict:
        """Compare two configuration versions.
        
        Args:
            version_id1: First version ID
            version_id2: Second version ID
            
        Returns:
            Dict: Comparison results
        """
        v1 = self.show_version(version_id1)
        v2 = self.show_version(version_id2)
        
        if not v1 or not v2:
            return {'error': 'One or both versions not found'}
        
        c1 = v1['config']
        c2 = v2['config']
        
        # Get all unique keys
        all_keys = set(c1.keys()).union(set(c2.keys()))
        
        added = [k for k in all_keys if k not in c1 and k in c2]
        removed = [k for k in all_keys if k in c1 and k not in c2]
        changed = [k for k in all_keys if k in c1 and k in c2 and c1[k] != c2[k]]
        
        return {
            'added': added,
            'removed': removed,
            'changed': changed,
            'unchanged': len(all_keys) - len(added) - len(removed) - len(changed)
        }
    
    def clean_old_versions(self, days: int) -> int:
        """Clean up versions older than specified days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            int: Number of versions deleted
        """
        if days <= 0:
            logging.error("Days must be a positive number")
            return 0
        
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        deleted_count = 0
        
        # Get all tags to avoid deleting tagged versions
        tags = self.list_tags()
        tagged_versions = [tag_info['version_id'] for tag_info in tags.values()]
        
        for file_name in os.listdir(self.versions_dir):
            if file_name.endswith('.json') and not file_name == 'tags.json':
                file_path = os.path.join(self.versions_dir, file_name)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        version_id = data['metadata']['version_id']
                        
                        # Skip tagged versions
                        if version_id in tagged_versions:
                            logging.info(f"Skipping tagged version: {version_id}")
                            continue
                            
                        timestamp_str = data['metadata']['timestamp']
                        timestamp = datetime.fromisoformat(timestamp_str).timestamp()
                        
                        if timestamp < cutoff_date:
                            os.remove(file_path)
                            deleted_count += 1
                            logging.info(f"Deleted old version: {version_id}")
                except Exception as e:
                    logging.warning(f"Error processing version file {file_name}: {e}")
        
        return deleted_count
    
    def validate_version(self, version_id: str) -> tuple[bool, List[str]]:
        """Validate a specific version of the configuration."""
        version_data = self.show_version(version_id)
        if not version_data:
            return False, ["Version not found"]
            
        # Import validator
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from validate_config import ConfigValidator
        
        # Create temporary file for validation
        temp_config = os.path.join(self.versions_dir, f'temp_config_{version_id}.yaml')
        try:
            with open(temp_config, 'w') as f:
                yaml.dump(version_data['config'], f, default_flow_style=False)
                
            # Validate configuration
            validator = ConfigValidator(temp_config)
            is_valid, errors = validator.validate_config()
            
            return is_valid, errors
            
        finally:
            # Cleanup temporary file
            if os.path.exists(temp_config):
                os.remove(temp_config)
                
    def tag_version(self, version_id: str, tag: str, force: bool = False) -> bool:
        """Tag a specific version of the configuration."""
        version_data = self.show_version(version_id)
        if not version_data:
            logging.error(f"Version {version_id} not found")
            return False
            
        tag_path = os.path.join(self.versions_dir, 'tags.json')
        tags = {}
        
        # Load existing tags
        if os.path.exists(tag_path):
            with open(tag_path, 'r') as f:
                tags = json.load(f)
                
        # Check if tag already exists
        if tag in tags and not force:
            logging.error(f"Tag '{tag}' already exists. Use --force to overwrite")
            return False
            
        # Update tags
        tags[tag] = {
            'version_id': version_id,
            'timestamp': datetime.now().isoformat(),
            'metadata': version_data['metadata']
        }
        
        # Save tags
        with open(tag_path, 'w') as f:
            json.dump(tags, f, indent=2)
            
        logging.info(f"Tagged version {version_id} as '{tag}'")
        return True
        
    def list_tags(self) -> Dict:
        """List all configuration tags."""
        tag_path = os.path.join(self.versions_dir, 'tags.json')
        if not os.path.exists(tag_path):
            return {}
            
        with open(tag_path, 'r') as f:
            return json.load(f)
            
    def get_version_by_tag(self, tag: str) -> Optional[str]:
        """Get version ID from tag."""
        tags = self.list_tags()
        if tag in tags:
            return tags[tag]['version_id']
        return None
        
    def remove_tag(self, tag: str) -> bool:
        """Remove a configuration tag."""
        tag_path = os.path.join(self.versions_dir, 'tags.json')
        if not os.path.exists(tag_path):
            return False
            
        tags = {}
        with open(tag_path, 'r') as f:
            tags = json.load(f)
            
        if tag in tags:
            del tags[tag]
            with open(tag_path, 'w') as f:
                json.dump(tags, f, indent=2)
            logging.info(f"Removed tag '{tag}'")
            return True
            
        logging.error(f"Tag '{tag}' not found")
        return False


def main():
    """Main configuration management function."""
    parser = argparse.ArgumentParser(description='Manage configuration versions')
    parser.add_argument('--config', default='config/export_config.yaml',
                      help='Path to configuration file')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Save version
    save_parser = subparsers.add_parser('save', help='Save current configuration as a new version')
    save_parser.add_argument('--message', '-m', help='Version message')
    
    # List versions
    subparsers.add_parser('list', help='List all saved versions')
    
    # Show version
    show_parser = subparsers.add_parser('show', help='Show details of a specific version')
    show_parser.add_argument('version_id', help='Version ID')
    
    # Rollback
    rollback_parser = subparsers.add_parser('rollback', help='Roll back to a specific version')
    rollback_parser.add_argument('version_id', help='Version ID to roll back to')
    
    # Compare versions
    compare_parser = subparsers.add_parser('compare', help='Compare two versions')
    compare_parser.add_argument('version_id1', help='First version ID')
    compare_parser.add_argument('version_id2', help='Second version ID')
    
    # Clean old versions
    clean_parser = subparsers.add_parser('clean', help='Clean up old versions')
    clean_parser.add_argument('days', type=int, help='Keep versions newer than this many days')
    
    # Tag management
    tag_parser = subparsers.add_parser('tag', help='Tag management commands')
    tag_subparsers = tag_parser.add_subparsers(dest='tag_command')
    
    # Add tag
    add_tag_parser = tag_subparsers.add_parser('add', help='Add tag to version')
    add_tag_parser.add_argument('version_id', help='Version ID')
    add_tag_parser.add_argument('tag', help='Tag name')
    add_tag_parser.add_argument('--force', action='store_true',
                             help='Force overwrite existing tag')
    
    # List tags
    tag_subparsers.add_parser('list', help='List all tags')
    
    # Remove tag
    remove_tag_parser = tag_subparsers.add_parser('remove', help='Remove tag')
    remove_tag_parser.add_argument('tag', help='Tag to remove')
    
    # Show version by tag
    show_tag_parser = tag_subparsers.add_parser('show', help='Show version by tag')
    show_tag_parser.add_argument('tag', help='Tag name')
    
    # Validation
    validate_parser = subparsers.add_parser('validate', help='Validate version')
    validate_parser.add_argument('version_id', help='Version ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    config_file = args.config
    manager = ConfigManager(config_file=config_file)
    
    if args.command == 'save':
        version_id = manager.save_version(args.message)
        if version_id:
            print(f"Saved configuration as version {version_id}")
            return 0
        return 1
    
    elif args.command == 'list':
        versions = manager.list_versions()
        if versions:
            print("\nSaved Versions:")
            for v in versions:
                print(f"\nID: {v['version_id']}")
                print(f"Date: {v['timestamp']}")
                if v.get('message'):
                    print(f"Message: {v['message']}")
        else:
            print("No saved versions found")
        return 0
    
    elif args.command == 'show':
        version_data = manager.show_version(args.version_id)
        if version_data:
            print(yaml.dump(version_data, default_flow_style=False))
            return 0
        return 1
    
    elif args.command == 'rollback':
        if manager.rollback(args.version_id):
            print(f"Successfully rolled back to version {args.version_id}")
            return 0
        print(f"Failed to roll back to version {args.version_id}")
        return 1
    
    elif args.command == 'compare':
        result = manager.compare_versions(args.version_id1, args.version_id2)
        if 'error' in result:
            print(f"Error: {result['error']}")
            return 1
        
        print(f"\nComparison of {args.version_id1} and {args.version_id2}:")
        print(f"Added sections: {', '.join(result['added']) if result['added'] else 'None'}")
        print(f"Removed sections: {', '.join(result['removed']) if result['removed'] else 'None'}")
        print(f"Changed sections: {', '.join(result['changed']) if result['changed'] else 'None'}")
        print(f"Unchanged sections: {result['unchanged']}")
        return 0
    
    elif args.command == 'clean':
        count = manager.clean_old_versions(args.days)
        print(f"Cleaned up {count} old version(s)")
        return 0
        
    elif args.command == 'tag':
        if args.tag_command == 'add':
            if manager.tag_version(args.version_id, args.tag, args.force):
                print(f"Tagged version {args.version_id} as '{args.tag}'")
                return 0
            return 1
            
        elif args.tag_command == 'list':
            tags = manager.list_tags()
            if tags:
                print("\nConfiguration Tags:")
                for tag, info in tags.items():
                    print(f"\nTag: {tag}")
                    print(f"Version: {info['version_id']}")
                    print(f"Created: {info['timestamp']}")
                    if info['metadata'].get('message'):
                        print(f"Message: {info['metadata']['message']}")
            else:
                print("No tags found")
            return 0
            
        elif args.tag_command == 'remove':
            if manager.remove_tag(args.tag):
                print(f"Removed tag '{args.tag}'")
                return 0
            return 1
            
        elif args.tag_command == 'show':
            version_id = manager.get_version_by_tag(args.tag)
            if version_id:
                version_data = manager.show_version(version_id)
                if version_data:
                    print(yaml.dump(version_data, default_flow_style=False))
                    return 0
            print(f"Tag '{args.tag}' not found")
            return 1
            
    elif args.command == 'validate':
        is_valid, errors = manager.validate_version(args.version_id)
        if is_valid:
            print(f"Version {args.version_id} is valid")
            return 0
        else:
            print(f"\nVersion {args.version_id} validation failed:")
            for error in errors:
                print(f"- {error}")
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

