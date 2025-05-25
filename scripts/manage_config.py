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

# Constants
CONFIG_DIR = "config"
DEFAULT_CONFIG_FILE = "analysis_config.yaml"
BACKUP_DIR = "config/backups"
SCHEMA_FILE = "config/config_schema.yaml"

def setup_logging(log_file=None):
    """Configure logging for configuration management."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    if log_file is None:
        log_file = os.path.join(log_dir, f"config_management_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_file

def ensure_config_dir():
    """Ensure configuration directory exists."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)

def get_default_config():
    """Get default configuration structure."""
    return {
        "database": {
            "type": "sqlite",
            "path": "db/extension_inventory.db",
            "backup_enabled": True,
            "backup_interval": 86400,  # 24 hours
            "max_backups": 5
        },
        "prisma": {
            "enabled": False,
            "connection_url": "postgresql://username:password@localhost:5432/extensions",
            "schema_path": "prisma/schema.prisma",
            "migration_dir": "prisma/migrations",
            "pool_size": 5
        },
        "monitoring": {
            "enabled": True,
            "interval": 3600,  # 1 hour
            "alert_threshold": 90,  # percentage
            "log_metrics": True,
            "retention_days": 30
        },
        "metrics": {
            "collect": True,
            "format": ["json", "html"],
            "save_path": "metrics",
            "history_length": 90,  # days
        },
        "extensions": {
            "download_retries": 3,
            "parallel_downloads": 4,
            "verify_integrity": True,
            "auto_fix": True
        }
    }

def generate_default_config(config_path):
    """Generate default configuration file."""
    config = get_default_config()
    ensure_config_dir()
    
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        logging.info(f"Default configuration generated at {config_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to generate default configuration: {str(e)}")
        return False

def load_config(config_path):
    """Load configuration from file."""
    try:
        if not os.path.exists(config_path):
            logging.warning(f"Configuration file not found: {config_path}")
            return None
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logging.info(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logging.error(f"Failed to load configuration: {str(e)}")
        return None

def create_backup(config_path):
    """Create a backup of the configuration file."""
    if not os.path.exists(config_path):
        logging.warning(f"Cannot backup: file not found: {config_path}")
        return None
        
    backup_filename = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    try:
        shutil.copy2(config_path, backup_path)
        logging.info(f"Configuration backup created at {backup_path}")
        return backup_path
    except Exception as e:
        logging.error(f"Failed to create backup: {str(e)}")
        return None

def validate_config(config):
    """Validate configuration structure and values."""
    errors = []
    default_config = get_default_config()
    
    # Check if config is None or empty
    if not config:
        return ["Configuration is empty or None"]
    
    # Check for required top-level sections
    for section in default_config:
        if section not in config:
            errors.append(f"Missing required section: {section}")
            continue
            
        # Check section type
        if not isinstance(config[section], dict):
            errors.append(f"Section '{section}' should be a dictionary")
            continue
            
        # Check required keys in each section
        for key in default_config[section]:
            if key not in config[section]:
                errors.append(f"Missing required key: {section}.{key}")
    
    # Validate database settings
    if "database" in config and isinstance(config["database"], dict):
        db_config = config["database"]
        
        # Check database type
        if "type" in db_config and db_config["type"] not in ["sqlite", "postgresql"]:
            errors.append("Database type must be 'sqlite' or 'postgresql'")
        
        # Check path for SQLite
        if "path" in db_config and db_config.get("type") == "sqlite":
            if not db_config["path"]:
                errors.append("SQLite database path cannot be empty")
    
    # Validate prisma settings
    if "prisma" in config and isinstance(config["prisma"], dict):
        prisma_config = config["prisma"]
        
        # Check connection URL if enabled
        if prisma_config.get("enabled", False):
            if not prisma_config.get("connection_url"):
                errors.append("Prisma connection URL is required when Prisma is enabled")
    
    # Validate monitoring settings
    if "monitoring" in config and isinstance(config["monitoring"], dict):
        monitoring_config = config["monitoring"]
        
        # Check interval
        if "interval" in monitoring_config and not isinstance(monitoring_config["interval"], int):
            errors.append("Monitoring interval must be an integer")
        elif "interval" in monitoring_config and monitoring_config["interval"] < 60:
            errors.append("Monitoring interval must be at least 60 seconds")
    
    # Validate metrics settings
    if "metrics" in config and isinstance(config["metrics"], dict):
        metrics_config = config["metrics"]
        
        # Check formats
        if "format" in metrics_config and isinstance(metrics_config["format"], list):
            valid_formats = ["json", "html", "pdf", "text"]
            for fmt in metrics_config["format"]:
                if fmt not in valid_formats:
                    errors.append(f"Invalid metrics format: {fmt}. Must be one of {valid_formats}")
    
    return errors

def save_config(config, config_path):
    """Save configuration to file."""
    try:
        # Ensure directories exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Create backup first
        create_backup(config_path)
        
        # Save new config
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        logging.info(f"Configuration saved to {config_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to save configuration: {str(e)}")
        return False

def update_config(config_path, updates):
    """Update configuration with new values."""
    config = load_config(config_path)
    
    if not config:
        logging.error("Cannot update: failed to load configuration")
        return False
    
    # Create backup before modifying
    create_backup(config_path)
    
    # Apply updates
    updated = False
    for section, section_updates in updates.items():
        if section not in config:
            config[section] = {}
        
        for key, value in section_updates.items():
            if config[section].get(key) != value:
                config[section][key] = value
                updated = True
                logging.info(f"Updated {section}.{key} = {value}")
    
    if not updated:
        logging.info("No changes needed, configuration is already up to date")
        return True
    
    # Validate updated config
    errors = validate_config(config)
    if errors:
        logging.error("Validation failed after updates:")
        for error in errors:
            logging.error(f"- {error}")
        return False
    
    # Save updated config
    return save_config(config, config_path)

def cleanup_backups(max_backups=10, max_age_days=30):
    """Clean up old configuration backups."""
    if not os.path.exists(BACKUP_DIR):
        logging.info(f"No backup directory found at {BACKUP_DIR}")
        return
    
    backups = []
    for filename in os.listdir(BACKUP_DIR):
        if filename.startswith("config_backup_") and filename.endswith(".yaml"):
            file_path = os.path.join(BACKUP_DIR, filename)
            creation_time = os.path.getctime(file_path)
            backups.append((file_path, creation_time))
    
    # Sort by creation time (newest first)
    backups.sort(key=lambda x: x[1], reverse=True)
    
    # Remove old backups
    current_time = datetime.now().timestamp()
    max_age_seconds = max_age_days * 24 * 60 * 60
    
    for i, (file_path, creation_time) in enumerate(backups):
        # Remove if too many backups
        if i >= max_backups:
            os.remove(file_path)
            logging.info(f"Removed old backup: {file_path} (exceeded max count)")
            continue
        
        # Remove if too old
        age_seconds = current_time - creation_time
        if age_seconds > max_age_seconds:
            os.remove(file_path)
            logging.info(f"Removed old backup: {file_path} (exceeded max age)")

def compare_configs(config1_path, config2_path):
    """Compare two configuration files and report differences."""
    config1 = load_config(config1_path)
    config2 = load_config(config2_path)
    
    if not config1 or not config2:
        logging.error("Failed to load one or both configurations for comparison")
        return None
    
    differences = {}
    
    # Check for sections in config1 but not in config2
    for section in config1:
        if section not in config2:
            differences[section] = {"status": "removed"}
            continue
        
        section_diffs = {}
        
        # Check keys in this section
        for key, value in config1[section].items():
            if key not in config2[section]:
                section_diffs[key] = {"status": "removed", "old_value": value}
            elif value != config2[section][key]:
                section_diffs[key] = {
                    "status": "changed",
                    "old_value": value,
                    "new_value": config2[section][key]
                }
        
        # Check for new keys in config2
        for key, value in config2[section].items():
            if key not in config1[section]:
                section_diffs[key] = {"status": "added", "new_value": value}
        
        if section_diffs:
            differences[section] = section_diffs
    
    # Check for new sections in config2
    for section in config2:
        if section not in config1:
            differences[section] = {"status": "added"}
    
    return differences

def main():
    """Main function for the configuration management tool."""
    parser = argparse.ArgumentParser(description='Manage configuration files')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Initialize command
    init_parser = subparsers.add_parser('init', help='Initialize default configuration')
    init_parser.add_argument('--force', action='store_true', help='Overwrite existing configuration')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate configuration')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update configuration values')
    update_parser.add_argument('--section', required=True, help='Configuration section to update')
    update_parser.add_argument('--key', required=True, help='Configuration key to update')
    update_parser.add_argument('--value', required=True, help='New value')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create a backup of the configuration')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old backups')
    cleanup_parser.add_argument('--max-backups', type=int, default=10, help='Maximum number of backups to keep')
    cleanup_parser.add_argument('--max-age', type=int, default=30, help='Maximum age of backups in days')
    
    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare two configuration files')
    compare_parser.add_argument('--other', required=True, help='Path to the second configuration file')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export configuration to JSON')
    export_parser.add_argument('--output', required=True, help='Output JSON file path')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import configuration from JSON')
    import_parser.add_argument('--input', required=True, help='Input JSON file path')
    
    # Add common arguments
    parser.add_argument('--config', default=os.path.join(CONFIG_DIR, DEFAULT_CONFIG_FILE),
                        help=f'Configuration file path (default: {os.path.join(CONFIG_DIR, DEFAULT_CONFIG_FILE)})')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    # Process commands
    if args.command == 'init':
        if os.path.exists(args.config) and not args.force:
            logging.error(f"Configuration file already exists at {args.config}. Use --force to overwrite.")
            return 1
        
        if generate_default_config(args.config):
            logging.info("Configuration initialized successfully")
            return 0
        else:
            logging.error("Failed to initialize configuration")
            return 1
    
    elif args.command == 'validate':
        config = load_config(args.config)
        if not config:
            logging.error(f"Failed to load configuration from {args.config}")
            return 1
        
        errors = validate_config(config)
        if errors:
            logging.error("Configuration validation failed:")
            for error in errors:
                logging.error(f"- {error}")
            return 1
        else:
            logging.info("Configuration validation successful")
            return 0
    
    elif args.command == 'update':
        updates = {args.section: {args.key: args.value}}
        if update_config(args.config, updates):
            logging.info("Configuration updated successfully")
            return 0
        else:
            logging.error("Failed to update configuration")
            return 1
    
    elif args.command == 'backup':
        backup_path = create_backup(args.config)
        if backup_path:
            logging.info(f"Backup created at {backup_path}")
            return 0
        else:
            logging.error("Failed to create backup")
            return 1
    
    elif args.command == 'cleanup':
        cleanup_backups(args.max_backups, args.max_age)
        logging.info("Backup cleanup completed")
        return 0
    
    elif args.command == 'compare':
        differences = compare_configs(args.config, args.other)
        if differences is None:
            logging.error("Failed to compare configurations")
            return 1
        
        if not differences:
            logging.info("Configurations are identical")
        else:
            logging.info("Configuration differences:")
            for section, section_diffs in differences.items():
                if isinstance(section_diffs, dict) and "status" in section_diffs:
                    status = section_diffs["status"]
                    logging.info(f"Section '{section}': {status}")
                else:
                    logging.info(f"Section '{section}':")
                    for key, diff in section_diffs.items():
                        status = diff["status"]
                        if status == "changed":
                            logging.info(f"  - {key}: changed from '{diff['old_value']}' to '{diff['new_value']}'")
                        elif status == "added":
                            logging.info(f"  - {key}: added with value '{diff['new_value']}'")
                        elif status == "removed":
                            logging.info(f"  - {key}: removed (was '{diff['old_value']}')")
        
        return 0
    
    elif args.command == 'export':
        config = load_config(args.config)
        if not config:
            logging.error(f"Failed to load configuration from {args.config}")
            return 1
        
        try:
            with open(args.output, 'w') as f:
                json.dump(config, f, indent=2)
            logging.info(f"Configuration exported to {args.output}")
            return 0
        except Exception as e:
            logging.error(f"Failed to export configuration: {str(e)}")
            return 1
    
    elif args.command == 'import':
        try:
            with open(args.input, 'r') as f:
                config = json.load(f)
            
            errors = validate_config(config)
            if errors:
                logging.error("Imported configuration validation failed:")
                for error in errors:
                    logging.error(f"- {error}")
                return 1
            
            if save_config(config, args.config):
                logging.info("Configuration imported successfully")
                return 0
            else:
                logging.error("Failed to save imported configuration")
                return 1
        except Exception as e:
            logging.error(f"Failed to import configuration: {str(e)}")
            return 1
    
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3

import os
import sys
import yaml
import argparse
from datetime import datetime
from pathlib import Path

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Manage database metrics analysis configuration'
    )
    parser.add_argument(
        '--show',
        action='store_true',
        help='Show current configuration'
    )
    parser.add_argument(
        '--show-section',
        type=str,
        help='Show specific configuration section'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate current configuration'
    )
    parser.add_argument(
        '--validate-section',
        type=str,
        help='Validate specific configuration section'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset configuration to defaults'
    )
    parser.add_argument(
        '--update',
        type=str,
        help='Update a configuration value (format: path.to.key=value)'
    )
    parser.add_argument(
        '--export',
        type=str,
        help='Export configuration to specified file'
    )
    parser.add_argument(
        '--import',
        type=str,
        dest='import_file',
        help='Import configuration from specified file'
    )
    parser.add_argument(
        '--compare',
        type=str,
        help='Compare current configuration with specified file'
    )
    parser.add_argument(
        '--diff-format',
        choices=['text', 'color', 'json'],
        default='color',
        help='Output format for configuration comparison'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create a backup of current configuration'
    )
    parser.add_argument(
        '--list-backups',
        action='store_true',
        help='List available configuration backups'
    )
    parser.add_argument(
        '--restore',
        type=str,
        help='Restore configuration from specified backup file'
    )
    parser.add_argument(
        '--history',
        action='store_true',
        help='Show configuration change history'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Clean up old backups'
    )
    parser.add_argument(
        '--max-backups',
        type=int,
        default=10,
        help='Maximum number of backups to keep (default: 10)'
    )
    parser.add_argument(
        '--max-age',
        type=int,
        default=30,
        help='Maximum age of backups in days (default: 30)'
    )
    return parser.parse_args()

def get_default_config():
    """Return default configuration."""
    return {
        'thresholds': {
            'query_time': 1.0,
            'memory_growth': 20,
            'db_growth': 50,
            'error_rate': 0.1,
            'performance_degradation': 50
        },
        'reports': {
            'retention_days': 30,
            'plot_style': {
                'figure_size': [10, 6],
                'dpi': 100,
                'colors': {
                    'sqlite': '#1f77b4',
                    'postgres': '#2ca02c',
                    'performance': '#d62728',
                    'memory': '#ff7f0e'
                }
            }
        },
        'intervals': {
            'min_samples': 10,
            'compare_window': 5
        },
        'alert_levels': {
            'critical': ['query_time', 'error_rate'],
            'warning': ['memory_growth', 'db_growth'],
            'info': ['performance_degradation']
        },
        'recommendations': {
            'query_time': [
                "Add indexes to frequently queried columns",
                "Review and optimize complex queries",
                "Consider implementing query caching"
            ],
            'memory_growth': [
                "Implement periodic memory cleanup",
                "Review memory-intensive operations",
                "Consider implementing memory limits"
            ],
            'db_growth': [
                "Implement data archival strategy",
                "Review data retention policies",
                "Consider database partitioning"
            ],
            'error_rate': [
                "Review error logs for patterns",
                "Implement robust error handling",
                "Set up monitoring alerts"
            ],
            'performance_degradation': [
                "Analyze query execution plans",
                "Review database statistics",
                "Consider database maintenance tasks"
            ]
        }
    }

def validate_config(config):
    """Validate configuration structure and values."""
    errors = []
    
    # Required sections
    required_sections = ['thresholds', 'reports', 'intervals', 'alert_levels', 'recommendations']
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required section: {section}")
    
    if 'thresholds' in config:
        for key in ['query_time', 'memory_growth', 'db_growth', 'error_rate']:
            if key not in config['thresholds']:
                errors.append(f"Missing threshold: {key}")
            elif not isinstance(config['thresholds'][key], (int, float)):
                errors.append(f"Invalid threshold value for {key}")
    
    if 'intervals' in config:
        for key in ['min_samples', 'compare_window']:
            if key not in config['intervals']:
                errors.append(f"Missing interval: {key}")
            elif not isinstance(config['intervals'][key], int):
                errors.append(f"Invalid interval value for {key}")
    
    if 'alert_levels' in config:
        for level in ['critical', 'warning', 'info']:
            if level not in config['alert_levels']:
                errors.append(f"Missing alert level: {level}")
            elif not isinstance(config['alert_levels'][level], list):
                errors.append(f"Invalid alert level format for {level}")
    
    return errors

def validate_section(config, section):
    """Validate specific configuration section."""
    errors = []
    
    if section not in config:
        return [f"Section '{section}' not found in configuration"]
    
    if section == 'thresholds':
        for key in ['query_time', 'memory_growth', 'db_growth', 'error_rate']:
            if key not in config[section]:
                errors.append(f"Missing threshold: {key}")
            elif not isinstance(config[section][key], (int, float)):
                errors.append(f"Invalid threshold value for {key}")
                
    elif section == 'intervals':
        for key in ['min_samples', 'compare_window']:
            if key not in config[section]:
                errors.append(f"Missing interval: {key}")
            elif not isinstance(config[section][key], int):
                errors.append(f"Invalid interval value for {key}")
                
    elif section == 'alert_levels':
        for level in ['critical', 'warning', 'info']:
            if level not in config[section]:
                errors.append(f"Missing alert level: {level}")
            elif not isinstance(config[section][level], list):
                errors.append(f"Invalid alert level format for {level}")
                
    elif section == 'reports':
        if 'retention_days' not in config[section]:
            errors.append("Missing retention_days in reports")
        if 'plot_style' not in config[section]:
            errors.append("Missing plot_style in reports")
        elif 'colors' not in config[section]['plot_style']:
            errors.append("Missing colors in plot_style")
            
    elif section == 'recommendations':
        for alert_type in ['query_time', 'memory_growth', 'db_growth', 'error_rate']:
            if alert_type not in config[section]:
                errors.append(f"Missing recommendations for {alert_type}")
            elif not isinstance(config[section][alert_type], list):
                errors.append(f"Invalid recommendations format for {alert_type}")
    
    return errors

def format_config_value(value, indent=0):
    """Format configuration value for display."""
    indent_str = '  ' * indent
    if isinstance(value, dict):
        lines = [f"{indent_str}{k}: {format_config_value(v, indent+1)}" for k, v in value.items()]
        return '\n'.join(lines)
    elif isinstance(value, list):
        if not value:
            return '[]'
        return f"\n{indent_str}  - " + f"\n{indent_str}  - ".join(str(x) for x in value)
    else:
        return str(value)

def show_config(config, section=None):
    """Display current configuration or specific section."""
    if section:
        if section not in config:
            print(f"Error: Section '{section}' not found in configuration")
            sys.exit(1)
        print(f"\n{section}:")
        print(format_config_value(config[section], 1))
    else:
        print("\nCurrent Configuration:")
        print(format_config_value(config))

def update_config_value(config, path, value):
    """Update a configuration value using dot notation path."""
    try:
        # Convert string value to appropriate type
        if value.lower() in ['true', 'false']:
            value = value.lower() == 'true'
        elif value.replace('.', '').isdigit():
            value = float(value) if '.' in value else int(value)
        elif value.startswith('[') and value.endswith(']'):
            value = [x.strip() for x in value[1:-1].split(',')]
        
        # Navigate to the correct location
        parts = path.split('.')
        current = config
        for part in parts[:-1]:
            current = current[part]
        current[parts[-1]] = value
        return True
    except Exception as e:
        print(f"Error updating configuration: {str(e)}")
        return False

def compare_configs(current, other):
    """Compare two configurations and return differences."""
    differences = {
        'added': {},
        'removed': {},
        'modified': {}
    }
    
    def compare_recursive(current, other, path=''):
        if isinstance(current, dict) and isinstance(other, dict):
            # Compare dictionary keys
            current_keys = set(current.keys())
            other_keys = set(other.keys())
            
            # Find added and removed keys
            for key in other_keys - current_keys:
                differences['added'][f"{path}{key}"] = other[key]
            for key in current_keys - other_keys:
                differences['removed'][f"{path}{key}"] = current[key]
            
            # Compare common keys
            for key in current_keys & other_keys:
                new_path = f"{path}{key}." if path or key else key
                compare_recursive(current[key], other[key], new_path)
                
        elif isinstance(current, list) and isinstance(other, list):
            # Compare lists (order-sensitive)
            if current != other:
                differences['modified'][path.rstrip('.')] = {
                    'old': current,
                    'new': other
                }
        else:
            # Compare values
            if current != other:
                differences['modified'][path.rstrip('.')] = {
                    'old': current,
                    'new': other
                }
    
    compare_recursive(current, other)
    return differences

def format_diff(differences, format_type='color'):
    """Format configuration differences for display."""
    if format_type == 'json':
        import json
        return json.dumps(differences, indent=2)
    
    output = []
    
    if format_type == 'color':
        # Define ANSI color codes
        GREEN = '\033[92m'
        RED = '\033[91m'
        YELLOW = '\033[93m'
        RESET = '\033[0m'
    else:
        # No colors for text format
        GREEN = RED = YELLOW = RESET = ''
    
    if differences['added']:
        output.append(f"\n{GREEN}Added Settings:{RESET}")
        for path, value in differences['added'].items():
            output.append(f"{GREEN}+ {path}: {value}{RESET}")
    
    if differences['removed']:
        output.append(f"\n{RED}Removed Settings:{RESET}")
        for path, value in differences['removed'].items():
            output.append(f"{RED}- {path}: {value}{RESET}")
    
    if differences['modified']:
        output.append(f"\n{YELLOW}Modified Settings:{RESET}")
        for path, change in differences['modified'].items():
            output.append(f"{YELLOW}~ {path}:{RESET}")
            output.append(f"  Old: {change['old']}")
            output.append(f"  New: {change['new']}")
    
    if not any(differences.values()):
        output.append("No differences found.")
    
    return '\n'.join(output)

def cleanup_old_backups(max_backups=10, max_age_days=30):
    """Clean up old backups based on count and age."""
    backup_dir = 'config/backups'
    if not os.path.exists(backup_dir):
        return
        
    backups = list_backups()
    removed = []
    
    # Remove backups older than max_age_days
    current_time = datetime.now()
    for backup in backups[:]:  # Create copy to modify during iteration
        try:
            backup_time = datetime.strptime(backup['timestamp'], '%Y%m%d_%H%M%S')
            age = (current_time - backup_time).days
            
            if age > max_age_days:
                os.remove(backup['path'])
                removed.append(backup['file'])
                backups.remove(backup)
        except Exception as e:
            print(f"Warning: Could not process backup {backup['file']}: {str(e)}")
    
    # Keep only max_backups most recent backups
    while len(backups) > max_backups:
        oldest = backups.pop()
        try:
            os.remove(oldest['path'])
            removed.append(oldest['file'])
        except Exception as e:
            print(f"Warning: Could not remove backup {oldest['file']}: {str(e)}")
    
    return removed

def create_backup(config, config_path):
    """Create a timestamped backup of the current configuration."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = 'config/backups'
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_path = os.path.join(backup_dir, f'config_backup_{timestamp}.yaml')
    
    try:
        with open(backup_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
            
        # Create a history entry
        history_path = os.path.join(backup_dir, 'history.log')
        with open(history_path, 'a') as f:
            f.write(f"{timestamp}: Backup created before configuration change\n")
        
        # Cleanup old backups
        removed = cleanup_old_backups()
        if removed:
            with open(history_path, 'a') as f:
                f.write(f"{timestamp}: Cleaned up old backups: {', '.join(removed)}\n")
            
        return backup_path
    except Exception as e:
        print(f"Warning: Failed to create backup: {str(e)}")
        return None

def list_backups():
    """List available configuration backups."""
    backup_dir = 'config/backups'
    if not os.path.exists(backup_dir):
        print("No backups found")
        return []
        
    backups = []
    for file in os.listdir(backup_dir):
        if file.startswith('config_backup_') and file.endswith('.yaml'):
            path = os.path.join(backup_dir, file)
            timestamp = file[13:-5]  # Extract timestamp from filename
            size = os.path.getsize(path)
            backups.append({
                'file': file,
                'path': path,
                'timestamp': timestamp,
                'size': size
            })
    
    return sorted(backups, key=lambda x: x['timestamp'], reverse=True)

def restore_backup(backup_path, config_path):
    """Restore configuration from a backup."""
    try:
        # Load and validate backup
        with open(backup_path, 'r') as f:
            backup_config = yaml.safe_load(f)
            
        errors = validate_config(backup_config)
        if errors:
            print("Invalid configuration in backup:")
            for error in errors:
                print(f"- {error}")
            return False
            
        # Create backup of current config before restore
        create_backup(backup_config, config_path)
        
        # Restore backup
        with open(config_path, 'w') as f:
            yaml.dump(backup_config, f, default_flow_style=False)
            
        # Log restoration
        history_path = os.path.join('config/backups', 'history.log')
        with open(history_path, 'a') as f:
            f.write(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}: Configuration restored from {os.path.basename(backup_path)}\n")
            
        return True
    except Exception as e:
        print(f"Error restoring backup: {str(e)}")
        return False

def show_history(limit=10):
    """Show configuration change history."""
    history_path = os.path.join('config/backups', 'history.log')
    if not os.path.exists(history_path):
        print("No configuration history found")
        return
        
    try:
        with open(history_path, 'r') as f:
            lines = f.readlines()
            
        print("\nConfiguration History:")
        print("-" * 50)
        for line in lines[-limit:]:
            print(line.strip())
    except Exception as e:
        print(f"Error reading history: {str(e)}")

def main():
    """Main configuration management function."""
    args = parse_arguments()
    config_path = 'config/analysis_config.yaml'
    
    # Load current configuration
    current_config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            current_config = yaml.safe_load(f)
    
    if args.cleanup:
        removed = cleanup_old_backups(args.max_backups, args.max_age)
        if removed:
            print(f"Cleaned up {len(removed)} old backups:")
            for backup in removed:
                print(f"- {backup}")
        else:
            print("No backups needed cleaning")
            
    elif args.backup:
        backup_path = create_backup(current_config, config_path)
        if backup_path:
            print(f"Backup created: {backup_path}")
    
    elif args.list_backups:
        backups = list_backups()
        if backups:
            print("\nAvailable Backups:")
            print("-" * 50)
            for backup in backups:
                print(f"{backup['timestamp']}: {backup['file']} ({backup['size']} bytes)")
    
    elif args.restore:
        if restore_backup(args.restore, config_path):
            print("Configuration restored successfully")
        else:
            sys.exit(1)
    
    elif args.history:
        show_history()
    
    elif args.compare:
        try:
            # Load comparison configuration
            with open(args.compare, 'r') as f:
                other_config = yaml.safe_load(f)
            
            # Compare configurations
            differences = compare_configs(current_config, other_config)
            
            # Display differences
            print(format_diff(differences, args.diff_format))
            
        except Exception as e:
            print(f"Error comparing configurations: {str(e)}")
            sys.exit(1)
    
    elif args.show:
        show_config(current_config)
        
    elif args.show_section:
        show_config(current_config, args.show_section)
        
    elif args.validate:
        errors = validate_config(current_config)
        if errors:
            print("Configuration validation failed:")
            for error in errors:
                print(f"- {error}")
            sys.exit(1)
        else:
            print("Configuration validation successful")
            
    elif args.validate_section:
        errors = validate_section(current_config, args.validate_section)
        if errors:
            print(f"Section '{args.validate_section}' validation failed:")
            for error in errors:
                print(f"- {error}")
            sys.exit(1)
        else:
            print(f"Section '{args.validate_section}' validation successful")
    
    elif args.reset:
        # Create backup before resetting
        create_backup(current_config, config_path)
        default_config = get_default_config()
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        print("Configuration reset to defaults")
    
    elif args.update:
        # Create backup before updating
        create_backup(current_config, config_path)
        try:
            path, value = args.update.split('=', 1)
            if update_config_value(current_config, path, value):
                with open(config_path, 'w') as f:
                    yaml.dump(current_config, f, default_flow_style=False)
                print(f"Updated {path} = {value}")
            else:
                print("Failed to update configuration")
                sys.exit(1)
        except ValueError:
            print("Invalid update format. Use: path.to.key=value")
            sys.exit(1)
    
    elif args.export:
        try:
            with open(args.export, 'w') as f:
                yaml.dump(current_config, f, default_flow_style=False)
            print(f"Configuration exported to {args.export}")
        except Exception as e:
            print(f"Error exporting configuration: {str(e)}")
            sys.exit(1)
    
    elif args.import_file:
        # Create backup before importing
        create_backup(current_config, config_path)
        try:
            with open(args.import_file, 'r') as f:
                new_config = yaml.safe_load(f)
            errors = validate_config(new_config)
            if errors:
                print("Invalid configuration in import file:")
                for error in errors:
                    print(f"- {error}")
                sys.exit(1)
            with open(config_path, 'w') as f:
                yaml.dump(new_config, f, default_flow_style=False)
            print(f"Configuration imported from {args.import_file}")
        except Exception as e:
            print(f"Error importing configuration: {str(e)}")
            sys.exit(1)
    
    else:
        print("No action specified. Use --help for usage information.")

if __name__ == "__main__":
    main()

