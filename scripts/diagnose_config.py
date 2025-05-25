#!/usr/bin/env python3

import os
import sys
import yaml
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class ConfigDiagnostics:
    def __init__(self, config_path: str, schema_path: str):
        self.config_path = config_path
        self.schema_path = schema_path
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging for diagnostics."""
        log_dir = "logs/diagnostics"
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"config_diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
    def load_files(self) -> tuple:
        """Load configuration and schema files."""
        try:
            with open(self.config_path) as f:
                config = yaml.safe_load(f)
            with open(self.schema_path) as f:
                schema = yaml.safe_load(f)
            return config, schema
        except Exception as e:
            logging.error(f"Failed to load files: {str(e)}")
            return None, None
            
    def validate_types(self, config: Dict) -> List[str]:
        """Validate data types against schema."""
        errors = []
        
        def check_type(value: Any, schema_type: str, path: str) -> None:
            if schema_type == 'integer' and not isinstance(value, int):
                errors.append(f"Type mismatch at {path}: expected integer, got {type(value).__name__}")
            elif schema_type == 'string' and not isinstance(value, str):
                errors.append(f"Type mismatch at {path}: expected string, got {type(value).__name__}")
            elif schema_type == 'boolean' and not isinstance(value, bool):
                errors.append(f"Type mismatch at {path}: expected boolean, got {type(value).__name__}")
            elif schema_type == 'array' and not isinstance(value, list):
                errors.append(f"Type mismatch at {path}: expected array, got {type(value).__name__}")
                
        def validate_recursive(data: Any, schema: Dict, path: str = '') -> None:
            if 'type' in schema:
                check_type(data, schema['type'], path)
                
            if schema.get('type') == 'object' and 'properties' in schema:
                for key, prop_schema in schema['properties'].items():
                    if key in data:
                        new_path = f"{path}.{key}" if path else key
                        validate_recursive(data[key], prop_schema, new_path)
                        
            elif schema.get('type') == 'array' and 'items' in schema:
                if isinstance(data, list):
                    for i, item in enumerate(data):
                        validate_recursive(item, schema['items'], f"{path}[{i}]")
                        
        validate_recursive(config, schema)
        return errors
        
    def validate_constraints(self, config: Dict) -> List[str]:
        """Validate value constraints from schema."""
        errors = []
        
        def check_constraints(value: Any, schema: Dict, path: str) -> None:
            if 'minimum' in schema and value < schema['minimum']:
                errors.append(f"Value at {path} ({value}) is below minimum {schema['minimum']}")
            if 'maximum' in schema and value > schema['maximum']:
                errors.append(f"Value at {path} ({value}) is above maximum {schema['maximum']}")
            if 'enum' in schema and value not in schema['enum']:
                errors.append(f"Value at {path} ({value}) not in allowed values: {schema['enum']}")
                
        def validate_recursive(data: Any, schema: Dict, path: str = '') -> None:
            if 'type' in schema:
                if schema['type'] == 'object' and 'properties' in schema:
                    for key, prop_schema in schema['properties'].items():
                        if key in data:
                            new_path = f"{path}.{key}" if path else key
                            validate_recursive(data[key], prop_schema, new_path)
                            check_constraints(data[key], prop_schema, new_path)
                            
        validate_recursive(config, schema)
        return errors
        
    def check_dependencies(self, config: Dict) -> List[str]:
        """Check for configuration dependencies."""
        warnings = []
        
        # Check Prisma configuration
        if config.get('prisma', {}).get('enabled'):
            if not config.get('prisma', {}).get('connection_url'):
                warnings.append("Prisma is enabled but connection_url is not set")
                
        # Check monitoring configuration
        if config.get('monitoring', {}).get('enabled'):
            if not config.get('monitoring', {}).get('log_metrics'):
                warnings.append("Monitoring is enabled but log_metrics is disabled")
                
        # Check backup configuration
        if config.get('database', {}).get('backup_enabled'):
            backup_interval = config.get('database', {}).get('backup_interval', 0)
            if backup_interval < 3600:
                warnings.append("Backup interval is less than 1 hour")
                
        return warnings
        
    def check_paths(self, config: Dict) -> List[str]:
        """Validate path configurations."""
        errors = []
        
        # Check database path
        db_path = config.get('database', {}).get('path')
        if db_path:
            db_dir = os.path.dirname(db_path)
            if not os.path.exists(db_dir):
                errors.append(f"Database directory does not exist: {db_dir}")
            elif not os.access(db_dir, os.W_OK):
                errors.append(f"Database directory is not writable: {db_dir}")
                
        # Check metrics save path
        metrics_path = config.get('metrics', {}).get('save_path')
        if metrics_path and not os.path.exists(metrics_path):
            errors.append(f"Metrics directory does not exist: {metrics_path}")
            
        return errors
        
    def analyze_performance_impact(self, config: Dict) -> Dict:
        """Analyze potential performance impact of configuration."""
        impact = {
            'status': 'ok',
            'warnings': [],
            'recommendations': []
        }
        
        # Check database connections
        pool_size = config.get('prisma', {}).get('pool_size', 0)
        if pool_size > 10:
            impact['warnings'].append("High database pool size may consume excessive resources")
            impact['recommendations'].append("Consider reducing pool_size if not needed")
            
        # Check monitoring interval
        monitor_interval = config.get('monitoring', {}).get('interval', 0)
        if monitor_interval < 300:  # 5 minutes
            impact['warnings'].append("Very frequent monitoring may impact performance")
            impact['recommendations'].append("Consider increasing monitoring interval")
            
        # Check metrics collection
        if config.get('metrics', {}).get('collect'):
            formats = config.get('metrics', {}).get('format', [])
            if len(formats) > 2:
                impact['warnings'].append("Multiple metric formats may increase storage usage")
                impact['recommendations'].append("Consider reducing number of metric formats")
            
        # Check backup configuration
        backup_interval = config.get('database', {}).get('backup_interval', 0)
        if backup_interval < 7200 and config.get('database', {}).get('backup_enabled'):
            impact['warnings'].append("Frequent backups may impact system performance")
            impact['recommendations'].append("Consider increasing backup interval")
            
        return impact
        
    def analyze_history(self) -> Dict:
        """Analyze configuration change history."""
        history_file = os.path.join('config/backups', 'history.log')
        changes = {
            'total_changes': 0,
            'last_change': None,
            'frequent_sections': {},
            'change_patterns': []
        }
        
        if not os.path.exists(history_file):
            return changes
            
        try:
            with open(history_file, 'r') as f:
                lines = f.readlines()
                
            changes['total_changes'] = len(lines)
            if lines:
                # Parse last change
                last_line = lines[-1].strip()
                changes['last_change'] = {
                    'timestamp': last_line.split(': ')[0],
                    'action': last_line.split(': ')[1]
                }
                
                # Analyze change patterns
                section_changes = {}
                for line in lines:
                    for section in ['database', 'prisma', 'monitoring', 'metrics']:
                        if section in line.lower():
                            section_changes[section] = section_changes.get(section, 0) + 1
                            
                changes['frequent_sections'] = dict(sorted(
                    section_changes.items(),
                    key=lambda x: x[1],
                    reverse=True
                ))
                
                # Detect patterns
                if len(lines) >= 3:
                    recent_changes = lines[-3:]
                    if all('backup' in line for line in recent_changes):
                        changes['change_patterns'].append("Frequent backup changes detected")
                    if all('monitoring' in line for line in recent_changes):
                        changes['change_patterns'].append("Frequent monitoring changes detected")
                        
        except Exception as e:
            logging.error(f"Error analyzing history: {str(e)}")
            
        return changes
        
    def check_security(self, config: Dict) -> List[str]:
        """Check for security concerns in configuration."""
        concerns = []
        
        # Check database configuration
        if config.get('database', {}).get('type') == 'postgresql':
            conn_url = config.get('prisma', {}).get('connection_url', '')
            if 'password' in conn_url and not conn_url.startswith('${'):
                concerns.append("Database password exposed in connection URL")
                
        # Check file permissions
        for path_key in ['path', 'save_path', 'schema_path']:
            for section in config.values():
                if isinstance(section, dict) and path_key in section:
                    path = section[path_key]
                    if os.path.exists(path):
                        mode = os.stat(path).st_mode
                        if mode & 0o777 == 0o777:
                            concerns.append(f"Overly permissive file permissions on {path}")
                            
        # Check monitoring configuration
        if config.get('monitoring', {}).get('enabled'):
            if not config.get('monitoring', {}).get('alert_threshold'):
                concerns.append("Monitoring enabled without alert threshold")
                
        return concerns
        
    def run_diagnostics(self) -> Dict:
        """Run all diagnostic checks."""
        config, schema = self.load_files()
        if not config or not schema:
            return {'status': 'error', 'message': 'Failed to load configuration files'}
            
        results = {
            'status': 'pass',
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'type_validation': {'status': 'pass', 'errors': []},
                'constraints': {'status': 'pass', 'errors': []},
                'dependencies': {'status': 'pass', 'warnings': []},
                'paths': {'status': 'pass', 'errors': []},
                'security': {'status': 'pass', 'concerns': []},
                'performance': {'status': 'pass', 'analysis': {}},
                'history': {'status': 'pass', 'analysis': {}}
            }
        }
        
        # Run basic validation checks
        type_errors = self.validate_types(config)
        if type_errors:
            results['checks']['type_validation']['status'] = 'fail'
            results['checks']['type_validation']['errors'] = type_errors
            results['status'] = 'fail'
            
        constraint_errors = self.validate_constraints(config)
        if constraint_errors:
            results['checks']['constraints']['status'] = 'fail'
            results['checks']['constraints']['errors'] = constraint_errors
            results['status'] = 'fail'
            
        dependency_warnings = self.check_dependencies(config)
        if dependency_warnings:
            results['checks']['dependencies']['status'] = 'warn'
            results['checks']['dependencies']['warnings'] = dependency_warnings
            
        path_errors = self.check_paths(config)
        if path_errors:
            results['checks']['paths']['status'] = 'fail'
            results['checks']['paths']['errors'] = path_errors
            results['status'] = 'fail'
        
        # Run new checks
        security_concerns = self.check_security(config)
        if security_concerns:
            results['checks']['security']['status'] = 'fail'
            results['checks']['security']['concerns'] = security_concerns
            results['status'] = 'fail'
            
        performance_analysis = self.analyze_performance_impact(config)
        if performance_analysis['warnings']:
            results['checks']['performance']['status'] = 'warn'
        results['checks']['performance']['analysis'] = performance_analysis
        
        history_analysis = self.analyze_history()
        results['checks']['history']['analysis'] = history_analysis
            
        return results

def main():
    """Main function for configuration diagnostics."""
    config_path = 'config/analysis_config.yaml'
    schema_path = 'config/config_schema.yaml'
    
    diagnostics = ConfigDiagnostics(config_path, schema_path)
    results = diagnostics.run_diagnostics()
    
    # Print results
    print("\nConfiguration Diagnostics Results:")
    print("=" * 40)
    print(f"Status: {results['status'].upper()}")
    print(f"Timestamp: {results['timestamp']}")
    print("\nChecks:")
    
    for check_name, check_results in results['checks'].items():
        print(f"\n{check_name.replace('_', ' ').title()}:")
        print("-" * 20)
        
        if check_results['status'] == 'fail':
            print(f"Status: FAIL")
            if 'errors' in check_results:
                for error in check_results.get('errors', []):
                    print(f"  - {error}")
            if 'concerns' in check_results:
                for concern in check_results.get('concerns', []):
                    print(f"  - {concern}")
        elif check_results['status'] == 'warn':
            print(f"Status: WARNING")
            for warning in check_results.get('warnings', []):
                print(f"  - {warning}")
            if check_name == 'performance' and 'analysis' in check_results:
                analysis = check_results['analysis']
                if analysis.get('recommendations'):
                    print("\n  Recommendations:")
                    for rec in analysis.get('recommendations', []):
                        print(f"  - {rec}")
        else:
            print(f"Status: PASS")
            
        # Special handling for history analysis
        if check_name == 'history' and 'analysis' in check_results:
            analysis = check_results['analysis']
            if analysis.get('total_changes', 0) > 0:
                print(f"\n  Total configuration changes: {analysis['total_changes']}")
                if analysis.get('last_change'):
                    print(f"  Last change: {analysis['last_change']['timestamp']} - {analysis['last_change']['action']}")
                if analysis.get('frequent_sections'):
                    print("\n  Most frequently changed sections:")
                    for section, count in list(analysis['frequent_sections'].items())[:3]:
                        print(f"  - {section}: {count} changes")
                if analysis.get('change_patterns'):
                    print("\n  Change patterns detected:")
                    for pattern in analysis['change_patterns']:
                        print(f"  - {pattern}")
            
    # Save results
    results_dir = "logs/diagnostics"
    os.makedirs(results_dir, exist_ok=True)
    results_file = os.path.join(results_dir, f"diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: {results_file}")

if __name__ == "__main__":
    main()

