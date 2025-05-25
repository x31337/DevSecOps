#!/usr/bin/env python3

import os
import sys
import yaml
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any
import re

class ConfigValidator:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging for validation."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
    def validate_config(self) -> tuple:
        """Validate the entire configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            return False, [f"Failed to load configuration: {str(e)}"]
            
        errors = []
        
        # Validate each section
        validators = {
            'defaults': self._validate_defaults,
            'validation': self._validate_validation_rules,
            'aggregation': self._validate_aggregation,
            'formats': self._validate_formats,
            'performance': self._validate_performance,
            'logging': self._validate_logging,
            'error_handling': self._validate_error_handling,
            'notifications': self._validate_notifications,
            'customization': self._validate_customization
        }
        
        for section, validator in validators.items():
            if section not in config:
                errors.append(f"Missing required section: {section}")
            else:
                section_errors = validator(config[section])
                errors.extend(section_errors)
                
        return len(errors) == 0, errors
        
    def _validate_defaults(self, config: Dict) -> List[str]:
        """Validate default settings."""
        errors = []
        
        required = {'format', 'output_dir', 'validate', 'aggregate', 'include_history'}
        for field in required:
            if field not in config:
                errors.append(f"Missing required default setting: {field}")
                
        if 'format' in config and config['format'] not in ['excel', 'csv', 'json']:
            errors.append("Invalid default format. Must be 'excel', 'csv', or 'json'")
            
        if 'output_dir' in config and not isinstance(config['output_dir'], str):
            errors.append("output_dir must be a string")
            
        return errors
        
    def _validate_validation_rules(self, config: Dict) -> List[str]:
        """Validate validation rules configuration."""
        errors = []
        
        required = {'required_fields', 'valid_statuses', 'timestamp_format'}
        for field in required:
            if field not in config:
                errors.append(f"Missing required validation rule: {field}")
                
        if 'timestamp_format' in config:
            try:
                import datetime
                datetime.datetime.now().strftime(config['timestamp_format'])
            except ValueError:
                errors.append(f"Invalid timestamp format: {config['timestamp_format']}")
                
        if 'max_error_length' in config and not isinstance(config['max_error_length'], int):
            errors.append("max_error_length must be an integer")
            
        return errors
        
    def _validate_aggregation(self, config: Dict) -> List[str]:
        """Validate aggregation settings."""
        errors = []
        
        required = {'summary_metrics', 'trend_metrics', 'default_window', 'min_data_points'}
        for field in required:
            if field not in config:
                errors.append(f"Missing required aggregation setting: {field}")
                
        if 'default_window' in config:
            if not isinstance(config['default_window'], int) or config['default_window'] < 1:
                errors.append("default_window must be a positive integer")
                
        if 'min_data_points' in config:
            if not isinstance(config['min_data_points'], int) or config['min_data_points'] < 1:
                errors.append("min_data_points must be a positive integer")
                
        return errors
        
    def _validate_formats(self, config: Dict) -> List[str]:
        """Validate export format configurations."""
        errors = []
        
        required_formats = {'excel', 'csv', 'json'}
        for fmt in required_formats:
            if fmt not in config:
                errors.append(f"Missing required format configuration: {fmt}")
                
        if 'excel' in config:
            if 'sheets' not in config['excel']:
                errors.append("Excel configuration missing 'sheets' section")
            else:
                for sheet in config['excel']['sheets']:
                    if 'name' not in sheet or 'include' not in sheet:
                        errors.append("Excel sheet configuration must include 'name' and 'include'")
                        
        return errors
        
    def _validate_performance(self, config: Dict) -> List[str]:
        """Validate performance settings."""
        errors = []
        
        if 'chunk_size' in config and not isinstance(config['chunk_size'], int):
            errors.append("chunk_size must be an integer")
            
        if 'max_memory' in config:
            if not isinstance(config['max_memory'], str):
                errors.append("max_memory must be a string with unit (e.g., '256M')")
            elif not re.match(r'^\d+[KMG]B?$', config['max_memory']):
                errors.append("Invalid max_memory format. Use format like '256M'")
                
        return errors
        
    def _validate_logging(self, config: Dict) -> List[str]:
        """Validate logging configuration."""
        errors = []
        
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if 'level' in config and config['level'] not in valid_levels:
            errors.append(f"Invalid logging level. Must be one of: {', '.join(valid_levels)}")
            
        if 'max_log_size' in config:
            if not isinstance(config['max_log_size'], str):
                errors.append("max_log_size must be a string with unit (e.g., '10M')")
            elif not re.match(r'^\d+[KMG]B?$', config['max_log_size']):
                errors.append("Invalid max_log_size format. Use format like '10M'")
                
        return errors
        
    def _validate_error_handling(self, config: Dict) -> List[str]:
        """Validate error handling configuration."""
        errors = []
        
        if 'retry_attempts' in config:
            if not isinstance(config['retry_attempts'], int) or config['retry_attempts'] < 0:
                errors.append("retry_attempts must be a non-negative integer")
                
        if 'retry_delay' in config:
            if not isinstance(config['retry_delay'], int) or config['retry_delay'] < 0:
                errors.append("retry_delay must be a non-negative integer")
                
        return errors
        
    def _validate_notifications(self, config: Dict) -> List[str]:
        """Validate notification settings."""
        errors = []
        
        for service in ['email', 'slack']:
            if service in config:
                if not isinstance(config[service].get('enabled'), bool):
                    errors.append(f"{service} enabled flag must be a boolean")
                    
                if config[service].get('enabled'):
                    if service == 'email':
                        if not config[service].get('smtp_server'):
                            errors.append("SMTP server required when email notifications are enabled")
                        if not config[service].get('recipients'):
                            errors.append("Recipients required when email notifications are enabled")
                    elif service == 'slack':
                        if not config[service].get('webhook_url'):
                            errors.append("Webhook URL required when Slack notifications are enabled")
                            
        return errors
        
    def _validate_customization(self, config: Dict) -> List[str]:
        """Validate customization settings."""
        errors = []
        
        if 'color_scheme' in config:
            for status in ['pass', 'warn', 'fail', 'info']:
                if status not in config['color_scheme']:
                    errors.append(f"Missing color for status: {status}")
                elif not re.match(r'^#[0-9A-Fa-f]{6}$', config['color_scheme'][status]):
                    errors.append(f"Invalid color format for {status}. Use hex format: #RRGGBB")
                    
        return errors
        
    def fix_config(self) -> tuple:
        """Attempt to fix common configuration issues."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            return False, [f"Failed to load configuration: {str(e)}"], None
            
        fixes_applied = []
        
        # Add missing sections with defaults
        default_sections = {
            'defaults': {
                'format': 'excel',
                'output_dir': 'logs/diagnostics/exports',
                'validate': True,
                'aggregate': True,
                'include_history': True
            },
            'validation': {
                'required_fields': ['file_timestamp', 'status', 'checks'],
                'valid_statuses': ['pass', 'warn', 'fail', 'unknown'],
                'timestamp_format': '%Y-%m-%d %H:%M:%S'
            },
            'aggregation': {
                'summary_metrics': ['total_checks', 'error_counts', 'warning_counts'],
                'trend_metrics': ['error_rate', 'performance'],
                'default_window': 7,
                'min_data_points': 3
            }
        }
        
        for section, defaults in default_sections.items():
            if section not in config:
                config[section] = defaults
                fixes_applied.append(f"Added missing section: {section}")
            else:
                for key, value in defaults.items():
                    if key not in config[section]:
                        config[section][key] = value
                        fixes_applied.append(f"Added missing key '{key}' to section '{section}'")
        
        # Fix common format issues
        if 'formats' in config:
            formats_config = config['formats']
            
            # Fix Excel configuration
            if 'excel' in formats_config:
                excel_config = formats_config['excel']
                if 'sheets' not in excel_config:
                    excel_config['sheets'] = [
                        {'name': 'Summary', 'include': True, 'position': 1},
                        {'name': 'Detailed Checks', 'include': True, 'position': 2},
                        {'name': 'Performance', 'include': True, 'position': 3}
                    ]
                    fixes_applied.append("Added default Excel sheets configuration")
                    
            # Ensure all required formats exist
            for fmt in ['excel', 'csv', 'json']:
                if fmt not in formats_config:
                    formats_config[fmt] = self._get_default_format_config(fmt)
                    fixes_applied.append(f"Added missing format configuration: {fmt}")
        
        # Fix performance settings
        if 'performance' in config:
            perf_config = config['performance']
            
            # Fix memory format
            if 'max_memory' in perf_config:
                if not isinstance(perf_config['max_memory'], str):
                    perf_config['max_memory'] = '256M'
                    fixes_applied.append("Fixed max_memory format")
                elif not re.match(r'^\d+[KMG]B?$', perf_config['max_memory']):
                    perf_config['max_memory'] = '256M'
                    fixes_applied.append("Fixed invalid max_memory value")
        
        # Fix logging configuration
        if 'logging' in config:
            log_config = config['logging']
            
            # Fix log level
            if 'level' in log_config and log_config['level'] not in {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}:
                log_config['level'] = 'INFO'
                fixes_applied.append("Fixed invalid logging level")
                
            # Fix log size format
            if 'max_log_size' in log_config:
                if not isinstance(log_config['max_log_size'], str):
                    log_config['max_log_size'] = '10M'
                    fixes_applied.append("Fixed max_log_size format")
                elif not re.match(r'^\d+[KMG]B?$', log_config['max_log_size']):
                    log_config['max_log_size'] = '10M'
                    fixes_applied.append("Fixed invalid max_log_size value")
        
        # Fix customization settings
        if 'customization' in config:
            custom_config = config['customization']
            
            # Fix color scheme
            if 'color_scheme' in custom_config:
                default_colors = {
                    'pass': '#28a745',
                    'warn': '#ffc107',
                    'fail': '#dc3545',
                    'info': '#17a2b8'
                }
                for status, color in default_colors.items():
                    if status not in custom_config['color_scheme']:
                        custom_config['color_scheme'][status] = color
                        fixes_applied.append(f"Added missing color for status: {status}")
                    elif not re.match(r'^#[0-9A-Fa-f]{6}$', custom_config['color_scheme'][status]):
                        custom_config['color_scheme'][status] = color
                        fixes_applied.append(f"Fixed invalid color format for status: {status}")
        
        # Validate the fixed configuration
        is_valid, errors = self.validate_config()
        
        if is_valid:
            # Save the fixed configuration
            try:
                # Create backup
                backup_path = f"{self.config_path}.bak"
                import shutil
                shutil.copy2(self.config_path, backup_path)
                
                # Save fixed config
                with open(self.config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                fixes_applied.append(f"Configuration backed up to: {backup_path}")
                
            except Exception as e:
                return False, [f"Failed to save fixed configuration: {str(e)}"], None
                
            return True, fixes_applied, config
        else:
            return False, [f"Configuration still invalid after fixes: {', '.join(errors)}"], None

    def _get_default_format_config(self, format_type: str) -> Dict:
        """Get default configuration for a specific format."""
        defaults = {
            'excel': {
                'sheets': [
                    {'name': 'Summary', 'include': True, 'position': 1},
                    {'name': 'Detailed Checks', 'include': True, 'position': 2},
                    {'name': 'Performance', 'include': True, 'position': 3}
                ]
            },
            'csv': {
                'flatten_nested': True,
                'include_metadata': True,
                'date_format': '%Y-%m-%d %H:%M:%S'
            },
            'json': {
                'pretty_print': True,
                'include_metadata': True,
                'compress_large': False
            }
        }
        return defaults.get(format_type, {})
        
    def analyze_config(self) -> Dict:
        """Analyze configuration and generate recommendations."""
        analysis = {
            'summary': {
                'valid': False,
                'total_issues': 0,
                'critical_issues': 0,
                'recommendations': []
            },
            'sections': {},
            'security': {
                'issues': [],
                'recommendations': []
            },
            'performance': {
                'issues': [],
                'recommendations': []
            }
        }
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            # Validate basic structure
            is_valid, errors = self.validate_config()
            analysis['summary']['valid'] = is_valid
            analysis['summary']['total_issues'] = len(errors)
            
            # Analyze each section
            for section in config:
                section_analysis = self._analyze_section(section, config[section])
                analysis['sections'][section] = section_analysis
                
                # Count critical issues
                if section_analysis.get('critical_issues'):
                    analysis['summary']['critical_issues'] += len(section_analysis['critical_issues'])
                
                # Aggregate recommendations
                if section_analysis.get('recommendations'):
                    analysis['summary']['recommendations'].extend(section_analysis['recommendations'])
            
            # Security analysis
            security_issues = self._analyze_security(config)
            analysis['security'] = security_issues
            
            # Performance analysis
            perf_issues = self._analyze_performance(config)
            analysis['performance'] = perf_issues
            
            return analysis
            
        except Exception as e:
            logging.error(f"Error analyzing configuration: {str(e)}")
            return analysis

    def _analyze_section(self, section: str, config: Dict) -> Dict:
        """Analyze a specific configuration section."""
        analysis = {
            'status': 'ok',
            'issues': [],
            'critical_issues': [],
            'recommendations': []
        }
        
        if section == 'defaults':
            if config.get('validate') is False:
                analysis['issues'].append("Data validation is disabled")
                analysis['recommendations'].append("Enable data validation for better data quality")
                
        elif section == 'performance':
            if config.get('chunk_size', 0) > 5000:
                analysis['issues'].append("Large chunk size may impact memory usage")
                analysis['recommendations'].append("Consider reducing chunk size for better memory management")
                
        elif section == 'logging':
            if config.get('level', '').upper() == 'DEBUG':
                analysis['issues'].append("Debug logging may impact performance")
                analysis['recommendations'].append("Use INFO level for production environments")
                
        return analysis

    def _analyze_security(self, config: Dict) -> Dict:
        """Analyze security configuration."""
        analysis = {
            'issues': [],
            'recommendations': []
        }
        
        # Check notification settings
        if 'notifications' in config:
            notif_config = config['notifications']
            
            # Check email security
            if notif_config.get('email', {}).get('enabled'):
                email_config = notif_config['email']
                if not email_config.get('use_tls'):
                    analysis['issues'].append("Email notifications not using TLS")
                    analysis['recommendations'].append("Enable TLS for secure email communications")
                    
        # Check logging security
        if 'logging' in config:
            log_config = config['logging']
            if log_config.get('level', '').upper() == 'DEBUG':
                analysis['issues'].append("Debug logging may expose sensitive information")
                analysis['recommendations'].append("Use appropriate logging level in production")
                
        return analysis

    def _analyze_performance(self, config: Dict) -> Dict:
        """Analyze performance configuration."""
        analysis = {
            'issues': [],
            'recommendations': []
        }
        
        # Check memory settings
        if 'performance' in config:
            perf_config = config['performance']
            
            # Parse memory limit
            if 'max_memory' in perf_config:
                memory_str = perf_config['max_memory']
                match = re.match(r'^(\d+)([KMG])B?$', memory_str)
                if match:
                    size, unit = match.groups()
                    size = int(size)
                    if unit == 'K' and size < 1024:
                        analysis['issues'].append("Memory limit may be too low")
                        analysis['recommendations'].append("Consider increasing memory limit")
                    elif unit == 'G' and size > 4:
                        analysis['issues'].append("High memory limit may impact system performance")
                        analysis['recommendations'].append("Consider optimizing memory usage")
                        
            # Check parallel processing
            if not perf_config.get('parallel_processing') and perf_config.get('chunk_size', 0) > 1000:
                analysis['recommendations'].append("Enable parallel processing for better performance with large chunks")
                
        return analysis

    def generate_report(self, output_format='text') -> str:
        """Generate a detailed configuration analysis report."""
        analysis = self.analyze_config()
        
        if output_format == 'json':
            return json.dumps(analysis, indent=2)
            
        # Text format
        report = []
        report.append("Configuration Analysis Report")
        report.append("=" * 30)
        report.append("")
        
        # Summary
        report.append("Summary")
        report.append("-" * 7)
        report.append(f"Status: {'Valid' if analysis['summary']['valid'] else 'Invalid'}")
        report.append(f"Total Issues: {analysis['summary']['total_issues']}")
        report.append(f"Critical Issues: {analysis['summary']['critical_issues']}")
        report.append("")
        
        # Section Analysis
        report.append("Section Analysis")
        report.append("-" * 15)
        for section, details in analysis['sections'].items():
            report.append(f"\n{section}:")
            if details['issues']:
                report.append("  Issues:")
                for issue in details['issues']:
                    report.append(f"  - {issue}")
            if details['recommendations']:
                report.append("  Recommendations:")
                for rec in details['recommendations']:
                    report.append(f"  - {rec}")
                    
        # Security Analysis
        report.append("\nSecurity Analysis")
        report.append("-" * 16)
        if analysis['security']['issues']:
            report.append("Issues:")
            for issue in analysis['security']['issues']:
                report.append(f"- {issue}")
        if analysis['security']['recommendations']:
            report.append("\nRecommendations:")
            for rec in analysis['security']['recommendations']:
                report.append(f"- {rec}")
                
        # Performance Analysis
        report.append("\nPerformance Analysis")
        report.append("-" * 19)
        if analysis['performance']['issues']:
            report.append("Issues:")
            for issue in analysis['performance']['issues']:
                report.append(f"- {issue}")
        if analysis['performance']['recommendations']:
            report.append("\nRecommendations:")
            for rec in analysis['performance']['recommendations']:
                report.append(f"- {rec}")
                
        return "\n".join(report)

def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description='Validate export configuration')
    parser.add_argument('--config', default='config/export_config.yaml',
                      help='Path to configuration file')
    parser.add_argument('--fix', action='store_true',
                      help='Attempt to fix common issues')
    parser.add_argument('--analyze', action='store_true',
                      help='Analyze configuration and generate recommendations')
    parser.add_argument('--report-format', choices=['text', 'json'], default='text',
                      help='Format for analysis report')
    
    validator = ConfigValidator(args.config)
    
    if args.analyze:
        print("Analyzing configuration...")
        report = validator.generate_report(args.report_format)
        
        if args.report_format == 'json':
            print(report)
        else:
            print(report)
            
        analysis = validator.analyze_config()
        return 0 if analysis['summary']['valid'] else 1
        
    elif args.fix:
        print("Attempting to fix configuration issues...")
        is_fixed, messages, _ = validator.fix_config()
        
        if is_fixed:
            print("\nConfiguration fixes applied successfully:")
            for message in messages:
                print(f"- {message}")
            print("\nValidating fixed configuration...")
            is_valid, _ = validator.validate_config()
            if is_valid:
                print("Configuration is now valid")
                return 0
            else:
                print("Some issues could not be automatically fixed. Please check the configuration manually.")
                return 1
        else:
            print("\nFailed to fix configuration:")
            for message in messages:
                print(f"- {message}")
            return 1
    else:
        is_valid, errors = validator.validate_config()
        
        if is_valid:
            print("Configuration validation successful")
            return 0
        else:
            print("\nConfiguration validation failed:")
            for error in errors:
                print(f"- {error}")
            print("\nTips:")
            print("- Run with '--fix' option to attempt automatic fixes")
            print("- Run with '--analyze' option to get detailed recommendations")
            return 1

if __name__ == "__main__":
    sys.exit(main())

