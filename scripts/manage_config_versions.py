#!/usr/bin/env python3

import os
import sys
import yaml
import json
import shutil
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class ConfigManager:
    def __init__(self, config_dir: str = 'config'):
        self.config_dir = config_dir
        self.versions_dir = os.path.join(config_dir, 'versions')
        self.setup_logging()
        self.ensure_directories()
        
    def setup_logging(self):
        """Configure logging for configuration management."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
    def ensure_directories(self):
        """Ensure required directories exist."""
        os.makedirs(self.versions_dir, exist_ok=True)
        
    def save_version(self, config_path: str, message: str = "") -> Optional[str]:
        """Save a new version of the configuration."""
        try:
            # Load and validate current config
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            # Generate version ID
            version_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            version_path = os.path.join(self.versions_dir, f'config_{version_id}.yaml')
            
            # Create version metadata
            metadata = {
                'version_id': version_id,
                'timestamp': datetime.now().isoformat(),
                'message': message,
                'config_file': os.path.basename(config_path)
            }
            
            # Save version with metadata
            version_data = {
                'metadata': metadata,
                'config': config
            }
            
            with open(version_path, 'w') as f:
                yaml.dump(version_data, f, default_flow_style=False)
                
            # Update version history
            self._update_history(metadata)
            
            logging.info(f"Saved configuration version: {version_id}")
            return version_id
            
        except Exception as e:
            logging.error(f"Failed to save version: {str(e)}")
            return None
            
    def _update_history(self, metadata: Dict):
        """Update version history file."""
        history_path = os.path.join(self.versions_dir, 'history.json')
        history = []
        
        if os.path.exists(history_path):
            with open(history_path, 'r') as f:
                history = json.load(f)
                
        history.append(metadata)
        
        with open(history_path, 'w') as f:
            json.dump(history, f, indent=2)
            
    def list_versions(self) -> List[Dict]:
        """List all available configuration versions."""
        history_path = os.path.join(self.versions_dir, 'history.json')
        if not os.path.exists(history_path):
            return []
            
        with open(history_path, 'r') as f:
            return json.load(f)
            
    def show_version(self, version_id: str) -> Optional[Dict]:
        """Show details of a specific version."""
        version_path = os.path.join(self.versions_dir, f'config_{version_id}.yaml')
        if not os.path.exists(version_path):
            logging.error(f"Version {version_id} not found")
            return None
            
        with open(version_path, 'r') as f:
            return yaml.safe_load(f)
            
    def rollback(self, version_id: str, config_path: str) -> bool:
        """Rollback to a specific version."""
        version_data = self.show_version(version_id)
        if not version_data:
            return False
            
        try:
            # Create backup of current config
            backup_path = f"{config_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            shutil.copy2(config_path, backup_path)
            
            # Write version data to config file
            with open(config_path, 'w') as f:
                yaml.dump(version_data['config'], f, default_flow_style=False)
                
            logging.info(f"Rolled back to version {version_id}")
            logging.info(f"Previous configuration backed up to {backup_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to rollback: {str(e)}")
            return False
            
    def compare_versions(self, version1: str, version2: str) -> Dict:
        """Compare two configuration versions."""
        v1_data = self.show_version(version1)
        v2_data = self.show_version(version2)
        
        if not v1_data or not v2_data:
            return {}
            
        v1_config = v1_data['config']
        v2_config = v2_data['config']
        
        differences = {
            'added': {},
            'removed': {},
            'modified': {}
        }
        
        # Compare sections
        all_sections = set(v1_config.keys()) | set(v2_config.keys())
        
        for section in all_sections:
            if section not in v1_config:
                differences['added'][section] = v2_config[section]
            elif section not in v2_config:
                differences['removed'][section] = v1_config[section]
            elif v1_config[section] != v2_config[section]:
                differences['modified'][section] = {
                    'old': v1_config[section],
                    'new': v2_config[section]
                }
                
        return differences
        
    def cleanup_old_versions(self, keep_days: int = 30) -> int:
        """Clean up old configuration versions."""
        cutoff = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
        removed = 0
        
        for file in os.listdir(self.versions_dir):
            if file.startswith('config_') and file.endswith('.yaml'):
                file_path = os.path.join(self.versions_dir, file)
                if os.path.getctime(file_path) < cutoff:
                    os.remove(file_path)
                    removed += 1
                    
        if removed > 0:
            logging.info(f"Removed {removed} old configuration versions")
            
        return removed

def main():
    """Main configuration management function."""
    parser = argparse.ArgumentParser(description='Manage configuration versions')
    parser.add_argument('--config', default='config/export_config.yaml',
                      help='Path to configuration file')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Save version
    save_parser = subparsers.add_parser('save', help='Save current configuration version')
    save_parser.add_argument('--message', help='Version message')
    
    # List versions
    subparsers.add_parser('list', help='List all configuration versions')
    
    # Show version
    show_parser = subparsers.add_parser('show', help='Show specific version')
    show_parser.add_argument('version_id', help='Version ID')
    
    # Rollback
    rollback_parser = subparsers.add_parser('rollback', help='Rollback to specific version')
    rollback_parser.add_argument('version_id', help='Version ID')
    
    # Compare versions
    compare_parser = subparsers.add_parser('compare', help='Compare two versions')
    compare_parser.add_argument('version1', help='First version ID')
    compare_parser.add_argument('version2', help='Second version ID')
    
    # Cleanup
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old versions')
    cleanup_parser.add_argument('--keep-days', type=int, default=30,
                              help='Days to keep versions')
    
    args = parser.parse_args()
    manager = ConfigManager()
    
    if args.command == 'save':
        version_id = manager.save_version(args.config, args.message)
        if version_id:
            print(f"Saved version: {version_id}")
            return 0
        return 1
        
    elif args.command == 'list':
        versions = manager.list_versions()
        if versions:
            print("\nConfiguration Versions:")
            for version in versions:
                print(f"\nVersion: {version['version_id']}")
                print(f"Time: {version['timestamp']}")
                if version.get('message'):
                    print(f"Message: {version['message']}")
        else:
            print("No versions found")
        return 0
        
    elif args.command == 'show':
        version_data = manager.show_version(args.version_id)
        if version_data:
            print(yaml.dump(version_data, default_flow_style=False))
            return 0
        return 1
        
    elif args.command == 'rollback':
        if manager.rollback(args.version_id, args.config):
            print(f"Successfully rolled back to version {args.version_id}")
            return 0
        return 1
        
    elif args.command == 'compare':
        differences = manager.compare_versions(args.version1, args.version2)
        if differences:
            print("\nConfiguration Differences:")
            print(yaml.dump(differences, default_flow_style=False))
            return 0
        return 1
        
    elif args.command == 'cleanup':
        removed = manager.cleanup_old_versions(args.keep_days)
        print(f"Removed {removed} old version(s)")
        return 0
        
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())

