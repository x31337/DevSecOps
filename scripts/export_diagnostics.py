#!/usr/bin/env python3

import os
import sys
import json
import csv
import logging
import argparse
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
import pandas as pd

class DiagnosticsExporter:
    def __init__(self, diagnostics_dir="logs/diagnostics"):
        self.diagnostics_dir = diagnostics_dir
        self.load_templates()
        
    def export_to_csv(self, data, output_file):
        """Export diagnostic data to CSV format."""
        flattened_data = []
        
        for entry in data:
            row = {
                'timestamp': entry['file_timestamp'],
                'overall_status': entry['status']
            }
            
            # Add check statuses
            for check, details in entry['checks'].items():
                row[f'{check}_status'] = details['status']
                if 'errors' in details:
                    row[f'{check}_errors'] = len(details['errors'])
                if 'warnings' in details:
                    row[f'{check}_warnings'] = len(details['warnings'])
                    
            flattened_data.append(row)
            
        df = pd.DataFrame(flattened_data)
        df.to_csv(output_file, index=False)
        return output_file
        
    def export_to_excel(self, data, output_file):
        """Export diagnostic data to Excel with multiple sheets."""
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = []
            for entry in data:
                summary_data.append({
                    'timestamp': entry['file_timestamp'],
                    'status': entry['status'],
                    'total_errors': sum(len(details.get('errors', [])) 
                                     for details in entry['checks'].values()),
                    'total_warnings': sum(len(details.get('warnings', [])) 
                                       for details in entry['checks'].values())
                })
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            # Detailed checks sheet
            checks_data = []
            for entry in data:
                for check, details in entry['checks'].items():
                    checks_data.append({
                        'timestamp': entry['file_timestamp'],
                        'check': check,
                        'status': details['status'],
                        'errors': len(details.get('errors', [])),
                        'warnings': len(details.get('warnings', []))
                    })
            pd.DataFrame(checks_data).to_excel(writer, sheet_name='Detailed Checks', index=False)
            
            # Performance analysis sheet
            perf_data = []
            for entry in data:
                if 'performance' in entry['checks']:
                    analysis = entry['checks']['performance'].get('analysis', {})
                    perf_data.append({
                        'timestamp': entry['file_timestamp'],
                        'warnings': len(analysis.get('warnings', [])),
                        'recommendations': len(analysis.get('recommendations', []))
                    })
            pd.DataFrame(perf_data).to_excel(writer, sheet_name='Performance', index=False)
            
        return output_file
        
    def load_templates(self):
        """Load report templates from templates directory."""
        self.templates = {}
        template_dir = "config/templates"
        if os.path.exists(template_dir):
            for file in os.listdir(template_dir):
                if file.endswith('.json'):
                    try:
                        with open(os.path.join(template_dir, file)) as f:
                            template = json.load(f)
                            self.templates[file[:-5]] = template
                    except Exception as e:
                        print(f"Error loading template {file}: {str(e)}")
                        
    def filter_data(self, data, filters):
        """Filter diagnostic data based on criteria."""
        filtered_data = []
        for entry in data:
            include = True
            
            # Apply filters
            for field, criteria in filters.items():
                if field == 'status':
                    if entry['status'] not in criteria:
                        include = False
                        break
                elif field == 'date_range':
                    timestamp = datetime.strptime(entry['timestamp'], '%Y-%m-%d %H:%M:%S')
                    if not (criteria['start'] <= timestamp <= criteria['end']):
                        include = False
                        break
                elif field == 'check_status':
                    for check, status in criteria.items():
                        if check in entry['checks'] and entry['checks'][check]['status'] not in status:
                            include = False
                            break
                elif field == 'error_threshold':
                    total_errors = sum(len(details.get('errors', [])) 
                                    for details in entry['checks'].values())
                    if total_errors > criteria:
                        include = False
                        break
                        
            if include:
                filtered_data.append(entry)
                
        return filtered_data
        
    def apply_template(self, data, template_name):
        """Apply a report template to the data."""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
            
        template = self.templates[template_name]
        processed_data = []
        
        for entry in data:
            processed_entry = {}
            
            # Apply template transformations
            for field, config in template['fields'].items():
                if config['type'] == 'direct':
                    # Direct field mapping
                    if field in entry:
                        processed_entry[config['output']] = entry[field]
                elif config['type'] == 'calculated':
                    # Calculated fields
                    if config['calculation'] == 'sum_errors':
                        processed_entry[config['output']] = sum(
                            len(details.get('errors', [])) 
                            for details in entry['checks'].values()
                        )
                    elif config['calculation'] == 'check_status':
                        processed_entry[config['output']] = {
                            check: details['status']
                            for check, details in entry['checks'].items()
                            if check in config.get('checks', [])
                        }
                        
            processed_data.append(processed_entry)
            
        return processed_data
        
    def create_template(self, name, fields, output_file=None):
        """Create a new report template."""
        template = {
            'name': name,
            'fields': fields,
            'created': datetime.now().isoformat()
        }
        
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(template, f, indent=2)
            self.templates[name] = template
            
        return template
        
    def validate_and_sanitize_data(self, data):
        """Validate and sanitize diagnostic data before export."""
        validated_data = []
        validation_errors = []
        
        for entry in data:
            try:
                # Validate entry structure
                if not isinstance(entry, dict):
                    validation_errors.append(f"Invalid entry type: {type(entry)}")
                    continue
                    
                sanitized_entry = {
                    'file_timestamp': self._validate_timestamp(entry.get('file_timestamp')),
                    'status': self._validate_status(entry.get('status')),
                    'checks': {}
                }
                
                # Validate and sanitize checks
                if 'checks' not in entry or not isinstance(entry['checks'], dict):
                    validation_errors.append(f"Missing or invalid checks in entry")
                    continue
                    
                for check_name, check_data in entry['checks'].items():
                    sanitized_check = self._validate_check(check_name, check_data)
                    if sanitized_check:
                        sanitized_entry['checks'][check_name] = sanitized_check
                    else:
                        validation_errors.append(f"Invalid check data for {check_name}")
                
                validated_data.append(sanitized_entry)
                
            except Exception as e:
                validation_errors.append(f"Error processing entry: {str(e)}")
        
        return validated_data, validation_errors

    def _validate_timestamp(self, timestamp):
        """Validate and format timestamp."""
        if isinstance(timestamp, str):
            try:
                dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(timestamp, datetime):
            return timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _validate_status(self, status):
        """Validate and normalize status."""
        valid_statuses = {'pass', 'warn', 'fail'}
        if isinstance(status, str) and status.lower() in valid_statuses:
            return status.lower()
        return 'unknown'

    def _validate_check(self, check_name, check_data):
        """Validate and sanitize check data."""
        if not isinstance(check_data, dict):
            return None
            
        sanitized_check = {
            'status': self._validate_status(check_data.get('status')),
            'errors': [],
            'warnings': []
        }
        
        # Validate errors
        if 'errors' in check_data and isinstance(check_data['errors'], list):
            sanitized_check['errors'] = [
                str(error) for error in check_data['errors']
                if error is not None
            ]
        
        # Validate warnings
        if 'warnings' in check_data and isinstance(check_data['warnings'], list):
            sanitized_check['warnings'] = [
                str(warning) for warning in check_data['warnings']
                if warning is not None
            ]
        
        # Validate analysis if present
        if 'analysis' in check_data and isinstance(check_data['analysis'], dict):
            sanitized_check['analysis'] = {
                'warnings': [],
                'recommendations': []
            }
            
            analysis = check_data['analysis']
            if 'warnings' in analysis and isinstance(analysis['warnings'], list):
                sanitized_check['analysis']['warnings'] = [
                    str(w) for w in analysis['warnings'] if w is not None
                ]
                
            if 'recommendations' in analysis and isinstance(analysis['recommendations'], list):
                sanitized_check['analysis']['recommendations'] = [
                    str(r) for r in analysis['recommendations'] if r is not None
                ]
        
        return sanitized_check

    def export_with_validation(self, data, output_file, format='excel', aggregation_config=None):
        """Export data with validation and sanitization."""
        # Validate and sanitize data
        validated_data, validation_errors = self.validate_and_sanitize_data(data)
        
        if validation_errors:
            print("\nValidation Warnings:")
            for error in validation_errors:
                print(f"- {error}")
        
        if not validated_data:
            raise ValueError("No valid data to export after validation")
        
        # Proceed with export using validated data
        if aggregation_config:
            return self.export_with_aggregation(validated_data, output_file, format, aggregation_config)
        elif format == 'excel':
            return self.export_to_excel(validated_data, output_file)
        elif format == 'csv':
            return self.export_to_csv(validated_data, output_file)
        else:  # json
            with open(output_file, 'w') as f:
                json.dump(validated_data, f, indent=2, default=str)
            return output_file
    
    def aggregate_data(self, data, aggregation_config):
        """Aggregate diagnostic data based on configuration."""
        aggregated = {
            'summary': self._calculate_summary_stats(data),
            'trends': self._analyze_trends(data),
            'critical_issues': self._identify_critical_issues(data),
            'recommendations': self._compile_recommendations(data)
        }
        
        if aggregation_config.get('custom_metrics'):
            aggregated['custom'] = self._calculate_custom_metrics(
                data, aggregation_config['custom_metrics']
            )
        
        return aggregated

    def _calculate_summary_stats(self, data):
        """Calculate summary statistics from diagnostic data."""
        summary = {
            'total_checks': len(data),
            'status_distribution': {
                'pass': 0,
                'warn': 0,
                'fail': 0
            },
            'error_counts': {
                'total': 0,
                'by_check': {}
            },
            'warning_counts': {
                'total': 0,
                'by_check': {}
            }
        }
        
        for entry in data:
            # Status distribution
            summary['status_distribution'][entry['status']] += 1
            
            # Error and warning counts
            for check, details in entry['checks'].items():
                errors = len(details.get('errors', []))
                warnings = len(details.get('warnings', []))
                
                summary['error_counts']['total'] += errors
                summary['warning_counts']['total'] += warnings
                
                if check not in summary['error_counts']['by_check']:
                    summary['error_counts']['by_check'][check] = 0
                if check not in summary['warning_counts']['by_check']:
                    summary['warning_counts']['by_check'][check] = 0
                    
                summary['error_counts']['by_check'][check] += errors
                summary['warning_counts']['by_check'][check] += warnings
        
        return summary

    def _analyze_trends(self, data):
        """Analyze trends in diagnostic data."""
        trends = {
            'status_changes': [],
            'error_rate': [],
            'performance_metrics': []
        }
        
        sorted_data = sorted(data, key=lambda x: x['file_timestamp'])
        for i, entry in enumerate(sorted_data):
            if i > 0:
                prev = sorted_data[i-1]
                # Track status changes
                if entry['status'] != prev['status']:
                    trends['status_changes'].append({
                        'timestamp': entry['file_timestamp'],
                        'from': prev['status'],
                        'to': entry['status']
                    })
            
            # Track error rates
            total_errors = sum(len(details.get('errors', [])) 
                             for details in entry['checks'].values())
            trends['error_rate'].append({
                'timestamp': entry['file_timestamp'],
                'count': total_errors
            })
            
            # Track performance metrics
            if 'performance' in entry['checks']:
                perf = entry['checks']['performance'].get('analysis', {})
                trends['performance_metrics'].append({
                    'timestamp': entry['file_timestamp'],
                    'warnings': len(perf.get('warnings', [])),
                    'recommendations': len(perf.get('recommendations', []))
                })
        
        return trends

    def _identify_critical_issues(self, data):
        """Identify critical issues from diagnostic data."""
        critical_issues = []
        
        for entry in data:
            issues = []
            # Check for security failures
            if ('security' in entry['checks'] and 
                entry['checks']['security']['status'] == 'fail'):
                for error in entry['checks']['security'].get('errors', []):
                    issues.append({
                        'type': 'security',
                        'severity': 'high',
                        'description': error
                    })
            
            # Check for performance degradation
            if ('performance' in entry['checks'] and 
                len(entry['checks']['performance'].get('analysis', {}).get('warnings', [])) > 2):
                issues.append({
                    'type': 'performance',
                    'severity': 'medium',
                    'description': 'Multiple performance warnings detected'
                })
            
            if issues:
                critical_issues.append({
                    'timestamp': entry['file_timestamp'],
                    'issues': issues
                })
        
        return critical_issues

    def _compile_recommendations(self, data):
        """Compile and prioritize recommendations."""
        all_recommendations = []
        
        for entry in data:
            for check, details in entry['checks'].items():
                if 'analysis' in details and 'recommendations' in details['analysis']:
                    for rec in details['analysis']['recommendations']:
                        all_recommendations.append({
                            'check': check,
                            'recommendation': rec,
                            'status': details['status']
                        })
        
        # Group and prioritize recommendations
        prioritized = {
            'high': [],
            'medium': [],
            'low': []
        }
        
        for rec in all_recommendations:
            if rec['status'] == 'fail':
                prioritized['high'].append(rec)
            elif rec['status'] == 'warn':
                prioritized['medium'].append(rec)
            else:
                prioritized['low'].append(rec)
        
        return prioritized

    def _calculate_custom_metrics(self, data, metrics_config):
        """Calculate custom metrics based on configuration."""
        results = {}
        
        for metric_name, config in metrics_config.items():
            if config['type'] == 'count':
                results[metric_name] = self._count_metric(data, config)
            elif config['type'] == 'ratio':
                results[metric_name] = self._ratio_metric(data, config)
            elif config['type'] == 'threshold':
                results[metric_name] = self._threshold_metric(data, config)
        
        return results
    
    def _count_metric(self, data, config):
        """Count occurrences of a condition in the data."""
        count = 0
        for entry in data:
            if config.get('field') in entry:
                if config.get('value') is None or entry[config['field']] == config['value']:
                    count += 1
            elif config.get('check') and config.get('status'):
                if (config['check'] in entry['checks'] and 
                    entry['checks'][config['check']]['status'] == config['status']):
                    count += 1
        return count
    
    def _ratio_metric(self, data, config):
        """Calculate ratio between two counts."""
        numerator = self._count_metric(data, config['numerator'])
        denominator = self._count_metric(data, config['denominator'])
        if denominator == 0:
            return 0
        return numerator / denominator
    
    def _threshold_metric(self, data, config):
        """Calculate threshold-based metric."""
        count = 0
        for entry in data:
            value = 0
            if config['field'] == 'errors':
                value = sum(len(details.get('errors', [])) 
                           for details in entry['checks'].values())
            elif config['field'] == 'warnings':
                value = sum(len(details.get('warnings', [])) 
                           for details in entry['checks'].values())
            
            if value >= config['threshold']:
                count += 1
        return count

    def generate_delta_report(self, current_data, previous_data, output_file, format='excel'):
        """Generate a report comparing two sets of diagnostic data."""
        delta = {
            'summary': self._compare_summaries(
                self._calculate_summary_stats(current_data),
                self._calculate_summary_stats(previous_data)
            ),
            'new_issues': self._identify_new_issues(current_data, previous_data),
            'resolved_issues': self._identify_resolved_issues(current_data, previous_data),
            'trend_changes': self._analyze_trend_changes(current_data, previous_data),
            'status_changes': self._compare_check_statuses(current_data, previous_data)
        }
        
        if format == 'excel':
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # Delta Summary
                summary_df = pd.DataFrame([{
                    'metric': key,
                    'previous': val['previous'],
                    'current': val['current'],
                    'change': val['change'],
                    'change_percentage': val['change_percentage']
                } for key, val in delta['summary'].items()])
                summary_df.to_excel(writer, sheet_name='Delta Summary', index=False)
                
                # New Issues
                if delta['new_issues']:
                    new_issues_df = pd.DataFrame(delta['new_issues'])
                    new_issues_df.to_excel(writer, sheet_name='New Issues', index=False)
                
                # Resolved Issues
                if delta['resolved_issues']:
                    resolved_df = pd.DataFrame(delta['resolved_issues'])
                    resolved_df.to_excel(writer, sheet_name='Resolved Issues', index=False)
                
                # Status Changes
                status_changes_df = pd.DataFrame(delta['status_changes'])
                status_changes_df.to_excel(writer, sheet_name='Status Changes', index=False)
                
                # Trend Analysis
                trend_df = pd.DataFrame(delta['trend_changes'])
                trend_df.to_excel(writer, sheet_name='Trend Analysis', index=False)
                
        elif format == 'json':
            with open(output_file, 'w') as f:
                json.dump(delta, f, indent=2, default=str)
                
        return output_file

    def _compare_summaries(self, current, previous):
        """Compare summary statistics between two periods."""
        delta = {}
        
        # Compare total checks
        delta['total_checks'] = {
            'previous': previous['total_checks'],
            'current': current['total_checks'],
            'change': current['total_checks'] - previous['total_checks'],
            'change_percentage': ((current['total_checks'] - previous['total_checks']) / 
                                previous['total_checks'] * 100 if previous['total_checks'] else 0)
        }
        
        # Compare status distributions
        for status in ['pass', 'warn', 'fail']:
            delta[f'{status}_count'] = {
                'previous': previous['status_distribution'][status],
                'current': current['status_distribution'][status],
                'change': current['status_distribution'][status] - previous['status_distribution'][status],
                'change_percentage': ((current['status_distribution'][status] - 
                                     previous['status_distribution'][status]) / 
                                    previous['status_distribution'][status] * 100 
                                    if previous['status_distribution'][status] else 0)
            }
        
        # Compare error and warning totals
        delta['total_errors'] = {
            'previous': previous['error_counts']['total'],
            'current': current['error_counts']['total'],
            'change': current['error_counts']['total'] - previous['error_counts']['total'],
            'change_percentage': ((current['error_counts']['total'] - 
                                 previous['error_counts']['total']) / 
                                previous['error_counts']['total'] * 100 
                                if previous['error_counts']['total'] else 0)
        }
        
        return delta

    def _identify_new_issues(self, current_data, previous_data):
        """Identify issues present in current data but not in previous."""
        previous_issues = set()
        current_issues = set()
        
        # Extract issues from previous data
        for entry in previous_data:
            for check, details in entry['checks'].items():
                for error in details.get('errors', []):
                    previous_issues.add(f"{check}:{error}")
        
        # Extract and compare issues from current data
        new_issues = []
        for entry in current_data:
            for check, details in entry['checks'].items():
                for error in details.get('errors', []):
                    issue_key = f"{check}:{error}"
                    if issue_key not in previous_issues:
                        new_issues.append({
                            'check': check,
                            'issue': error,
                            'first_seen': entry['file_timestamp']
                        })
        
        return new_issues

    def _identify_resolved_issues(self, current_data, previous_data):
        """Identify issues present in previous data but resolved in current."""
        current_issues = set()
        
        # Extract issues from current data
        for entry in current_data:
            for check, details in entry['checks'].items():
                for error in details.get('errors', []):
                    current_issues.add(f"{check}:{error}")
        
        # Compare with previous issues
        resolved_issues = []
        for entry in previous_data:
            for check, details in entry['checks'].items():
                for error in details.get('errors', []):
                    issue_key = f"{check}:{error}"
                    if issue_key not in current_issues:
                        resolved_issues.append({
                            'check': check,
                            'issue': error,
                            'last_seen': entry['file_timestamp']
                        })
        
        return resolved_issues

    def _analyze_trend_changes(self, current_data, previous_data):
        """Analyze changes in trends between periods."""
        current_trends = self._analyze_trends(current_data)
        previous_trends = self._analyze_trends(previous_data)
        
        changes = []
        
        # Compare error rates
        if current_trends['error_rate'] and previous_trends['error_rate']:
            current_avg = sum(e['count'] for e in current_trends['error_rate']) / len(current_trends['error_rate'])
            previous_avg = sum(e['count'] for e in previous_trends['error_rate']) / len(previous_trends['error_rate'])
            
            changes.append({
                'metric': 'Average Error Rate',
                'previous': previous_avg,
                'current': current_avg,
                'change': current_avg - previous_avg,
                'trend': 'Improving' if current_avg < previous_avg else 'Deteriorating'
            })
        
        # Compare performance metrics
        if current_trends['performance_metrics'] and previous_trends['performance_metrics']:
            current_warnings = sum(p['warnings'] for p in current_trends['performance_metrics'])
            previous_warnings = sum(p['warnings'] for p in previous_trends['performance_metrics'])
            
            changes.append({
                'metric': 'Performance Warnings',
                'previous': previous_warnings,
                'current': current_warnings,
                'change': current_warnings - previous_warnings,
                'trend': 'Improving' if current_warnings < previous_warnings else 'Deteriorating'
            })
        
        return changes

    def _compare_check_statuses(self, current_data, previous_data):
        """Compare check statuses between periods."""
        changes = []
        
        # Get latest entries from each period
        current_latest = max(current_data, key=lambda x: x['file_timestamp'])
        previous_latest = max(previous_data, key=lambda x: x['file_timestamp'])
        
        # Compare check statuses
        all_checks = set(current_latest['checks'].keys()) | set(previous_latest['checks'].keys())
        
        for check in all_checks:
            current_status = current_latest['checks'].get(check, {}).get('status', 'unknown')
            previous_status = previous_latest['checks'].get(check, {}).get('status', 'unknown')
            
            if current_status != previous_status:
                changes.append({
                    'check': check,
                    'previous_status': previous_status,
                    'current_status': current_status,
                    'timestamp': current_latest['file_timestamp']
                })
        
        return changes
        
    def export_with_aggregation(self, data, output_file, format='excel', aggregation_config=None):
        """Export data with aggregated statistics."""
        if aggregation_config:
            aggregated = self.aggregate_data(data, aggregation_config)
        else:
            aggregated = self.aggregate_data(data, {'custom_metrics': {}})
        
        if format == 'excel':
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # Export raw data sheets
                if isinstance(data, list) and data:
                    # Summary sheet
                    summary_data = []
                    for entry in data:
                        summary_data.append({
                            'timestamp': entry['file_timestamp'],
                            'status': entry['status'],
                            'total_errors': sum(len(details.get('errors', [])) 
                                             for details in entry['checks'].values()),
                            'total_warnings': sum(len(details.get('warnings', [])) 
                                               for details in entry['checks'].values())
                        })
                    pd.DataFrame(summary_data).to_excel(writer, sheet_name='Raw Data Summary', index=False)
                    
                    # Detailed checks sheet
                    checks_data = []
                    for entry in data:
                        for check, details in entry['checks'].items():
                            checks_data.append({
                                'timestamp': entry['file_timestamp'],
                                'check': check,
                                'status': details['status'],
                                'errors': len(details.get('errors', [])),
                                'warnings': len(details.get('warnings', []))
                            })
                    pd.DataFrame(checks_data).to_excel(writer, sheet_name='Detailed Checks', index=False)
                
                # Export aggregated data
                summary_df = pd.DataFrame([{
                    'total_checks': aggregated['summary']['total_checks'],
                    'pass_count': aggregated['summary']['status_distribution']['pass'],
                    'warn_count': aggregated['summary']['status_distribution']['warn'],
                    'fail_count': aggregated['summary']['status_distribution']['fail'],
                    'total_errors': aggregated['summary']['error_counts']['total'],
                    'total_warnings': aggregated['summary']['warning_counts']['total']
                }])
                summary_df.to_excel(writer, sheet_name='Summary Statistics', index=False)
                
                # Export error breakdown
                error_data = []
                for check, count in aggregated['summary']['error_counts']['by_check'].items():
                    error_data.append({
                        'check': check,
                        'error_count': count,
                        'warning_count': aggregated['summary']['warning_counts']['by_check'].get(check, 0)
                    })
                pd.DataFrame(error_data).to_excel(writer, sheet_name='Error Breakdown', index=False)
                
                # Export trends
                if aggregated['trends']['status_changes']:
                    pd.DataFrame(aggregated['trends']['status_changes']).to_excel(
                        writer, sheet_name='Status Changes', index=False)
                
                if aggregated['trends']['error_rate']:
                    pd.DataFrame(aggregated['trends']['error_rate']).to_excel(
                        writer, sheet_name='Error Rates', index=False)
                
                # Export critical issues
                if aggregated['critical_issues']:
                    issues_df = pd.DataFrame([{
                        'timestamp': issue['timestamp'],
                        'issue_count': len(issue['issues']),
                        'issues': '; '.join(i['description'] for i in issue['issues'])
                    } for issue in aggregated['critical_issues']])
                    issues_df.to_excel(writer, sheet_name='Critical Issues', index=False)
                
                # Export recommendations
                all_recs = []
                for priority, recs in aggregated['recommendations'].items():
                    for rec in recs:
                        all_recs.append({
                            'priority': priority,
                            'check': rec['check'],
                            'recommendation': rec['recommendation']
                        })
                if all_recs:
                    pd.DataFrame(all_recs).to_excel(writer, sheet_name='Recommendations', index=False)
                
                # Export custom metrics if any
                if 'custom' in aggregated:
                    custom_df = pd.DataFrame([aggregated['custom']])
                    custom_df.to_excel(writer, sheet_name='Custom Metrics', index=False)
        
        elif format == 'json':
            output = {
                'raw_data': data,
                'aggregated': aggregated
            }
            with open(output_file, 'w') as f:
                json.dump(output, f, indent=2, default=str)
        
        elif format == 'csv':
            # For CSV, export only the summary statistics
            summary_data = {
                'total_checks': aggregated['summary']['total_checks'],
                'pass_count': aggregated['summary']['status_distribution']['pass'],
                'warn_count': aggregated['summary']['status_distribution']['warn'],
                'fail_count': aggregated['summary']['status_distribution']['fail'],
                'total_errors': aggregated['summary']['error_counts']['total'],
                'total_warnings': aggregated['summary']['warning_counts']['total']
            }
            
            # Add error counts by check
            for check, count in aggregated['summary']['error_counts']['by_check'].items():
                summary_data[f'{check}_errors'] = count
                
            # Add warning counts by check
            for check, count in aggregated['summary']['warning_counts']['by_check'].items():
                summary_data[f'{check}_warnings'] = count
                
            # Add custom metrics if any
            if 'custom' in aggregated:
                for metric, value in aggregated['custom'].items():
                    summary_data[metric] = value
                    
            pd.DataFrame([summary_data]).to_csv(output_file, index=False)
        
        return output_file
    
    def get_quick_summary(self, data):
        """Generate a quick summary of the diagnostic data."""
        try:
            total_entries = len(data)
            latest_entry = max(data, key=lambda x: x['file_timestamp']) if data else None
            
            summary = {
                'total_entries': total_entries,
                'date_range': {
                    'start': min(d['file_timestamp'] for d in data) if data else None,
                    'end': max(d['file_timestamp'] for d in data) if data else None
                },
                'current_status': latest_entry['status'] if latest_entry else None,
                'issues_summary': {
                    'errors': sum(len(details.get('errors', [])) 
                                for entry in data 
                                for details in entry['checks'].values()),
                    'warnings': sum(len(details.get('warnings', [])) 
                                  for entry in data 
                                  for details in entry['checks'].values())
                }
            }
            
            if latest_entry:
                summary['checks_status'] = {
                    check: details['status']
                    for check, details in latest_entry['checks'].items()
                }
                
            return summary
        except Exception as e:
            logging.error(f"Error generating quick summary: {str(e)}")
            return None

    def export_quick_report(self, data, output_dir=None):
        """Generate a quick report with essential information."""
        if output_dir is None:
            output_dir = 'logs/diagnostics/quick_reports'
        
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            # Generate summary data
            summary = self.get_quick_summary(data)
            if not summary:
                raise ValueError("Failed to generate summary data")
            
            # Create report files
            report_files = {}
            
            # JSON summary
            json_file = os.path.join(output_dir, f'quick_summary_{timestamp}.json')
            with open(json_file, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            report_files['json'] = json_file
            
            # Excel report with key metrics
            excel_file = os.path.join(output_dir, f'quick_report_{timestamp}.xlsx')
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # Summary sheet
                pd.DataFrame([summary]).to_excel(writer, sheet_name='Summary', index=False)
                
                # Status history
                status_data = [{
                    'timestamp': entry['file_timestamp'],
                    'status': entry['status'],
                    'errors': sum(len(details.get('errors', [])) 
                                for details in entry['checks'].values()),
                    'warnings': sum(len(details.get('warnings', [])) 
                                  for details in entry['checks'].values())
                } for entry in data]
                pd.DataFrame(status_data).to_excel(writer, sheet_name='Status History', index=False)
            
            report_files['excel'] = excel_file
            
            return report_files
        except Exception as e:
            logging.error(f"Error generating quick report: {str(e)}")
            return None

    def handle_errors(func):
        """Decorator for error handling in export operations."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except FileNotFoundError as e:
                logging.error(f"File not found error: {str(e)}")
                raise
            except PermissionError as e:
                logging.error(f"Permission denied: {str(e)}")
                raise
            except ValueError as e:
                logging.error(f"Invalid data or parameter: {str(e)}")
                raise
            except Exception as e:
                logging.error(f"Unexpected error in {func.__name__}: {str(e)}")
                logging.debug(traceback.format_exc())
                raise
        return wrapper
        
    def create_report_config(self, output_file):
        """Create a default report configuration file."""
        config = {
            'report': {
                'title': 'Configuration Diagnostics Report',
                'company_name': '',
                'logo_path': '',
                'include_sections': ['summary', 'status', 'errors', 'performance', 'security'],
                'chart_style': {
                    'colors': {
                        'pass': '#28a745',
                        'warn': '#ffc107',
                        'fail': '#dc3545'
                    },
                    'font_family': 'Arial, sans-serif',
                    'chart_size': {'width': 800, 'height': 400}
                }
            },
            'notifications': {
                'email': {
                    'enabled': False,
                    'recipients': [],
                    'on_failure': True,
                    'on_warning': True
                },
                'slack': {
                    'enabled': False,
                    'webhook_url': '',
                    'channel': ''
                }
            },
            'thresholds': {
                'warning_threshold': 3,
                'error_threshold': 1,
                'performance_warning_threshold': 5
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2)
        return output_file

# Default template fields for quick template creation
DEFAULT_TEMPLATE_FIELDS = {
    'timestamp': {'type': 'direct', 'output': 'Time'},
    'status': {'type': 'direct', 'output': 'Overall Status'},
    'errors': {
        'type': 'calculated',
        'calculation': 'sum_errors',
        'output': 'Total Errors'
    },
    'critical_checks': {
        'type': 'calculated',
        'calculation': 'check_status',
        'checks': ['security', 'performance'],
        'output': 'Critical Status'
    }
}

def main():
    """Main function with enhanced error handling."""
    try:
        # Setup logging
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=os.path.join(log_dir, f"export_diagnostics_{datetime.now().strftime('%Y%m%d')}.log"),
            filemode='a'
        )
        
        # Add console handler for warnings and above
        console = logging.StreamHandler()
        console.setLevel(logging.WARNING)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
        
        parser = argparse.ArgumentParser(description='Export configuration diagnostics data')
    parser.add_argument('--format', choices=['csv', 'excel', 'json'], 
                      default='csv', help='Export format')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--create-config', action='store_true',
                      help='Create default report configuration')
    parser.add_argument('--template', help='Use specific report template')
    parser.add_argument('--create-template', help='Create new template with given name')
    parser.add_argument('--filter', help='JSON string with filter criteria')
    parser.add_argument('--list-templates', action='store_true',
                      help='List available report templates')
    parser.add_argument('--aggregate', action='store_true',
                      help='Enable data aggregation in export')
    parser.add_argument('--custom-metrics', help='JSON string with custom metrics configuration')
    parser.add_argument('--delta', help='Compare with previous data from specified date (YYYYMMDD format)')
    parser.add_argument('--delta-days', type=int, help='Compare with data from specified number of days ago')
    parser.add_argument('--validate', action='store_true', help='Validate and sanitize data before export')
    parser.add_argument('--quick-report', action='store_true',
                      help='Generate a quick summary report')
    args = parser.parse_args()
    
    # Initialize exporter
    try:
        exporter = DiagnosticsExporter()
        logging.info("DiagnosticsExporter initialized")
    except Exception as e:
        logging.error(f"Failed to initialize DiagnosticsExporter: {str(e)}")
        print(f"Error: Failed to initialize exporter: {str(e)}")
        return 1
    
    # Template operations
    if args.list_templates:
        templates = exporter.templates
        if not templates:
            print("No templates found")
            return 0
        print("\nAvailable Templates:")
        for name, template in templates.items():
            print(f"- {name}: {template.get('description', 'No description')}")
        return 0
        
    if args.create_template:
        try:
            output_file = f'config/templates/{args.create_template}.json'
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            exporter.create_template(args.create_template, DEFAULT_TEMPLATE_FIELDS, output_file)
            print(f"\nCreated template: {output_file}")
            return 0
        except Exception as e:
            logging.error(f"Error creating template: {str(e)}")
            print(f"Error creating template: {str(e)}")
            return 1
    
    # Configuration operations
    if args.create_config:
        try:
            config_file = 'config/report_config.json'
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            exporter.create_report_config(config_file)
            print(f"\nCreated report configuration: {config_file}")
            return 0
        except Exception as e:
            logging.error(f"Error creating configuration: {str(e)}")
            print(f"Error creating configuration: {str(e)}")
            return 1
        
    # Load and validate data
    try:
        logging.info("Loading diagnostic data")
        from visualize_diagnostics import DiagnosticsVisualizer
        visualizer = DiagnosticsVisualizer()
        data = visualizer.load_diagnostic_data()
        
        if not data:
            logging.warning("No diagnostic data found")
            print("No diagnostic data found")
            return 1
            
        # Generate quick summary before processing
        summary = exporter.get_quick_summary(data)
        if summary:
            print("\nData Overview:")
            print(f"Total entries: {summary['total_entries']}")
            print(f"Date range: {summary['date_range']['start']} to {summary['date_range']['end']}")
            print(f"Current status: {summary['current_status']}")
            print(f"Total issues: {summary['issues_summary']['errors']} errors, "
                  f"{summary['issues_summary']['warnings']} warnings")
            
        logging.info(f"Loaded {len(data)} diagnostic entries")
    except Exception as e:
        logging.error(f"Error loading diagnostic data: {str(e)}")
        print(f"Error loading diagnostic data: {str(e)}")
        return 1
        
    # Quick report option
    if args.quick_report:
        try:
            reports = exporter.export_quick_report(data)
            if reports:
                print("\nQuick reports generated:")
                for fmt, path in reports.items():
                    print(f"- {fmt.upper()}: {path}")
                return 0
            else:
                print("Failed to generate quick reports")
                return 1
        except Exception as e:
            logging.error(f"Error generating quick report: {str(e)}")
            print(f"Error generating quick report: {str(e)}")
            return 1
    
    # Apply filters if provided
    if args.filter:
        try:
            logging.info(f"Applying filters: {args.filter}")
            filters = json.loads(args.filter)
            filtered_data = exporter.filter_data(data, filters)
            
            if not filtered_data:
                logging.warning("No data remains after applying filters")
                print("Warning: No data remains after applying filters")
                return 1
                
            data = filtered_data
            print(f"\nApplied filters: {len(data)} entries remaining")
            logging.info(f"After filtering: {len(data)} entries remaining")
        except json.JSONDecodeError:
            logging.error("Invalid filter JSON")
            print("Error: Invalid filter JSON")
            return 1
        except Exception as e:
            logging.error(f"Error applying filters: {str(e)}")
            print(f"Error applying filters: {str(e)}")
            return 1
            
    # Apply template if specified
    if args.template:
        try:
            logging.info(f"Applying template: {args.template}")
            processed_data = exporter.apply_template(data, args.template)
            
            if not processed_data:
                logging.warning("Template resulted in empty data")
                print(f"Warning: Template {args.template} resulted in empty data")
                return 1
                
            data = processed_data
            print(f"\nApplied template: {args.template}")
        except ValueError as e:
            logging.error(f"Error applying template: {str(e)}")
            print(f"Error: {str(e)}")
            return 1
        except Exception as e:
            logging.error(f"Unexpected error applying template: {str(e)}")
            print(f"Error applying template: {str(e)}")
            return 1
        
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'logs/diagnostics/exports/diagnostics_{timestamp}.{args.format}'
        
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Handle delta report generation
    if args.delta or args.delta_days:
        # Get previous data
        previous_data = []
        
        if args.delta:
            # Load data from specific date
            try:
                target_date = datetime.strptime(args.delta, "%Y%m%d")
                
                # Find files from that date
                for file in os.listdir(exporter.diagnostics_dir):
                    if file.startswith("diagnostics_") and file.endswith(".json"):
                        file_timestamp = datetime.strptime(file[11:19], "%Y%m%d")
                        if file_timestamp.date() == target_date.date():
                            with open(os.path.join(exporter.diagnostics_dir, file), 'r') as f:
                                file_data = json.load(f)
                                previous_data.append(file_data)
                
            except ValueError:
                print("Error: Invalid date format. Use YYYYMMDD.")
                return
                
        elif args.delta_days:
            # Calculate date N days ago
            target_date = datetime.now() - timedelta(days=args.delta_days)
            
            # Load all data and filter by date
            all_data = visualizer.load_diagnostic_data()
            for entry in all_data:
                entry_date = datetime.strptime(str(entry['file_timestamp']), "%Y-%m-%d %H:%M:%S")
                if entry_date.date() <= target_date.date() and entry not in data:
                    previous_data.append(entry)
        
        if not previous_data:
            print(f"No previous data found for comparison")
            return
            
        print(f"Comparing current data ({len(data)} records) with previous data ({len(previous_data)} records)")
        
        if not args.output:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            args.output = f'logs/diagnostics/exports/delta_report_{timestamp}.{args.format}'
            
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        
        output_file = exporter.generate_delta_report(data, previous_data, args.output, args.format)
        print(f"\nDelta report generated: {output_file}")
        
    # Export data in requested format
    elif args.validate:
        # If validation is requested
        aggregation_config = None
        if args.aggregate:
            aggregation_config = {}
            if args.custom_metrics:
                try:
                    aggregation_config['custom_metrics'] = json.loads(args.custom_metrics)
                except json.JSONDecodeError:
                    print("Error: Invalid custom metrics JSON")
                    return
        
        try:
            output_file = exporter.export_with_validation(data, args.output, args.format, aggregation_config)
            print(f"\nData validated and exported to: {output_file}")
        except ValueError as e:
            print(f"Error: {str(e)}")
            return
    
    elif args.aggregate:
        # If aggregation is requested
        aggregation_config = {}
        if args.custom_metrics:
            try:
                aggregation_config['custom_metrics'] = json.loads(args.custom_metrics)
            except json.JSONDecodeError:
                print("Error: Invalid custom metrics JSON")
                return
        
        output_file = exporter.export_with_aggregation(data, args.output, args.format, aggregation_config)
        print(f"\nData exported with aggregation to: {output_file}")
    else:
        # Standard export without aggregation
        if args.format == 'csv':
            output_file = exporter.export_to_csv(data, args.output)
        elif args.format == 'excel':
            output_file = exporter.export_to_excel(data, args.output)
        else:  # json
            with open(args.output, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            output_file = args.output
        
    print(f"\nData exported to: {output_file}")

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Critical error: {str(e)}")
        logging.critical(f"Critical error: {str(e)}", exc_info=True)
        sys.exit(1)

