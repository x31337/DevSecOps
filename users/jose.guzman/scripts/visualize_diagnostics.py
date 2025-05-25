#!/usr/bin/env python3

import os
import json
import argparse
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

class DiagnosticsVisualizer:
    def __init__(self, diagnostics_dir="logs/diagnostics"):
        self.diagnostics_dir = diagnostics_dir
        self.setup_style()
        
    def setup_style(self):
        """Configure plotting style."""
        sns.set_theme(style="whitegrid")
        plt.rcParams['figure.figsize'] = [12, 8]
        plt.rcParams['figure.dpi'] = 100
        
    def load_diagnostic_data(self, days=7):
        """Load diagnostic results from the past N days."""
        data = []
        cutoff = datetime.now() - timedelta(days=days)
        
        for file in os.listdir(self.diagnostics_dir):
            if file.startswith("diagnostics_") and file.endswith(".json"):
                file_path = os.path.join(self.diagnostics_dir, file)
                try:
                    # Get file timestamp from filename
                    timestamp_str = file[11:-5]  # Extract YYYYMMDD_HHMMSS
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    if timestamp >= cutoff:
                        with open(file_path, 'r') as f:
                            result = json.load(f)
                            result['file_timestamp'] = timestamp
                            data.append(result)
                except Exception as e:
                    print(f"Error loading {file}: {str(e)}")
                    
        return sorted(data, key=lambda x: x['file_timestamp'])
        
    def plot_check_status_history(self, data, output_dir):
        """Plot history of check statuses."""
        timestamps = [d['file_timestamp'].strftime('%Y-%m-%d %H:%M') for d in data]
        checks = data[0]['checks'].keys()
        
        plt.figure(figsize=(15, 8))
        
        for i, check in enumerate(checks):
            statuses = [d['checks'][check]['status'] for d in data]
            status_values = [2 if s == 'pass' else 1 if s == 'warn' else 0 for s in statuses]
            plt.plot(timestamps, status_values, marker='o', label=check)
            
        plt.yticks([0, 1, 2], ['fail', 'warn', 'pass'])
        plt.xticks(rotation=45)
        plt.title('Check Status History')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'check_status_history.png'))
        plt.close()
        
    def plot_error_distribution(self, data, output_dir):
        """Plot distribution of errors and warnings."""
        error_counts = {}
        warning_counts = {}
        
        for result in data:
            for check, details in result['checks'].items():
                if 'errors' in details:
                    error_counts[check] = error_counts.get(check, 0) + len(details['errors'])
                if 'warnings' in details:
                    warning_counts[check] = warning_counts.get(check, 0) + len(details['warnings'])
                    
        plt.figure(figsize=(12, 6))
        x = range(len(error_counts))
        plt.bar(x, error_counts.values(), label='Errors', alpha=0.7)
        plt.bar(x, warning_counts.values(), bottom=list(error_counts.values()),
                label='Warnings', alpha=0.7)
        plt.xticks(x, error_counts.keys(), rotation=45)
        plt.title('Distribution of Errors and Warnings by Check Type')
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'error_distribution.png'))
        plt.close()
        
    def plot_performance_trends(self, data, output_dir):
        """Plot performance-related trends."""
        timestamps = [d['file_timestamp'].strftime('%Y-%m-%d %H:%M') for d in data]
        warnings = [len(d['checks']['performance']['analysis'].get('warnings', [])) for d in data]
        
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, warnings, marker='o', linestyle='-', linewidth=2)
        plt.title('Performance Warning Trends')
        plt.xlabel('Time')
        plt.ylabel('Number of Performance Warnings')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'performance_trends.png'))
        plt.close()
        
    def plot_security_heatmap(self, data, output_dir):
        """Create security concerns heatmap."""
        security_types = {
            'database': ['password', 'connection', 'credentials'],
            'permissions': ['permissive', 'permissions', 'access'],
            'monitoring': ['alert', 'threshold', 'notification'],
            'configuration': ['exposed', 'unprotected', 'insecure']
        }
        
        heatmap_data = []
        for result in data:
            concerns = result['checks']['security'].get('concerns', [])
            row = []
            for category, keywords in security_types.items():
                score = sum(1 for c in concerns if any(k in c.lower() for k in keywords))
                row.append(score)
            heatmap_data.append(row)
            
        plt.figure(figsize=(10, 6))
        sns.heatmap(heatmap_data, 
                   xticklabels=list(security_types.keys()),
                   yticklabels=[d['file_timestamp'].strftime('%Y-%m-%d') for d in data],
                   cmap='YlOrRd', annot=True)
        plt.title('Security Concerns Heatmap')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'security_heatmap.png'))
        plt.close()
        
    def add_interactive_charts(self):
        """Generate interactive chart JavaScript using Chart.js."""
        return """
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
        function createStatusChart(data) {
            const ctx = document.getElementById('statusChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: data,
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Check Status History (Interactive)'
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 2,
                            ticks: {
                                callback: function(value) {
                                    return ['Fail', 'Warn', 'Pass'][value];
                                }
                            }
                        }
                    }
                }
            });
        }

        function createTrendChart(data) {
            const ctx = document.getElementById('trendChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: data,
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Issue Trend Analysis'
                        }
                    }
                }
            });
        }
        </script>
        """

    def predict_trends(self, data):
        """Predict future trend based on historical data."""
        try:
            import numpy as np
            from scipy import stats
            
            # Extract performance warnings over time
            warnings = [len(d['checks']['performance']['analysis'].get('warnings', [])) for d in data]
            times = range(len(warnings))
            
            if len(warnings) < 2:
                return None
                
            # Calculate trend line
            slope, intercept, r_value, p_value, std_err = stats.linregress(times, warnings)
            
            # Predict next 3 points
            future_points = []
            for i in range(len(warnings), len(warnings) + 3):
                prediction = slope * i + intercept
                future_points.append(max(0, round(prediction, 2)))
                
            return {
                'trend_slope': slope,
                'confidence': r_value ** 2,
                'predictions': future_points,
                'significant': p_value < 0.05
            }
        except ImportError:
            return None
        
    def generate_report(self, data, output_dir):
        """Generate HTML report with visualizations."""
        report_template = """
        <html>
        <head>
            <title>Configuration Diagnostics Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .section { margin: 20px 0; padding: 20px; border: 1px solid #ccc; }
                .plot { margin: 20px 0; text-align: center; }
                img { max-width: 100%; }
                .summary { background: #f5f5f5; padding: 15px; }
            </style>
        </head>
        <body>
            <h1>Configuration Diagnostics Report</h1>
            <div class="summary">
                <h2>Analysis Summary</h2>
                <p>Period: {start_date} to {end_date}</p>
                <p>Total Diagnostics Run: {total_runs}</p>
            </div>
            
            <div class="section">
                <h2>Check Status History</h2>
                <div class="plot">
                    <img src="check_status_history.png" />
                </div>
            </div>
            
            <div class="section">
                <h2>Error Distribution</h2>
                <div class="plot">
                    <img src="error_distribution.png" />
                </div>
            </div>
            
            <div class="section">
                <h2>Performance Trends</h2>
                <div class="plot">
                    <img src="performance_trends.png" />
                </div>
            </div>
            
            <div class="section">
                <h2>Security Analysis</h2>
                <div class="plot">
                    <img src="security_heatmap.png" />
                </div>
            </div>
        """
        
        # Generate plots
        self.plot_check_status_history(data, output_dir)
        self.plot_error_distribution(data, output_dir)
        self.plot_performance_trends(data, output_dir)
        self.plot_security_heatmap(data, output_dir)
        
        # Add interactive charts and trend prediction
        trend_data = self.predict_trends(data)
        if trend_data:
            report_template += """
            <div class="section">
                <h2>Trend Analysis</h2>
                <div class="summary">
                    <p>Trend Direction: {trend_direction}</p>
                    <p>Confidence: {confidence:.2%}</p>
                    <p>Predicted Issues (Next 3 Checks): {predictions}</p>
                </div>
                <canvas id="trendChart"></canvas>
            </div>
            
            <div class="section">
                <h2>Interactive Status History</h2>
                <canvas id="statusChart"></canvas>
            </div>
            """
        
        # Add closing HTML tags
        report_template += """
        </body>
        </html>
        """
        
        # Create report data
        report_data = {
            'start_date': data[0]['file_timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
            'end_date': data[-1]['file_timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
            'total_runs': len(data),
            'trend_direction': 'Improving' if trend_data and trend_data['trend_slope'] < 0
                             else 'Deteriorating' if trend_data and trend_data['trend_slope'] > 0
                             else 'Stable',
            'confidence': trend_data['confidence'] if trend_data else 0,
            'predictions': ', '.join(map(str, trend_data['predictions'])) if trend_data else 'N/A'
        }
        
        # Generate the basic report content
        report_content = report_template.format(**report_data)
        
        # Add JavaScript for interactive charts if trend data is available
        if trend_data:
            # Add Chart.js library and functions
            report_content += self.add_interactive_charts()
            
            # Add chart data initialization
            chart_data_script = """
            <script>
            document.addEventListener('DOMContentLoaded', function() {
                const statusData = {
                    labels: %s,
                    datasets: %s
                };
                createStatusChart(statusData);
                
                const trendData = {
                    labels: %s,
                    datasets: [{
                        label: 'Actual',
                        data: %s,
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    }, {
                        label: 'Predicted',
                        data: %s,
                        borderColor: 'rgb(255, 99, 132)',
                        borderDash: [5, 5],
                        tension: 0.1
                    }]
                };
                createTrendChart(trendData);
            });
            </script>
            """ % (
                json.dumps([d['file_timestamp'].strftime('%Y-%m-%d %H:%M') for d in data]),
                json.dumps([{
                    'label': check,
                    'data': [2 if d['checks'][check]['status'] == 'pass' 
                            else 1 if d['checks'][check]['status'] == 'warn'
                            else 0 for d in data],
                    'borderColor': f'hsl({hash(check) % 360}, 70%, 50%)',
                    'tension': 0.1
                } for check in data[0]['checks'].keys()]),
                json.dumps([d['file_timestamp'].strftime('%Y-%m-%d %H:%M') for d in data] +
                          [f'Prediction {i+1}' for i in range(3)]),
                json.dumps([len(d['checks']['performance']['analysis'].get('warnings', [])) 
                           for d in data]),
                json.dumps([None] * len(data) + trend_data['predictions'])
            )
            
            report_content += chart_data_script
        
        # Write report to file
        report_path = os.path.join(output_dir, 'diagnostic_report.html')
        with open(report_path, 'w') as f:
            f.write(report_content)
            
        return report_path

def main():
    parser = argparse.ArgumentParser(description='Visualize configuration diagnostics results')
    parser.add_argument('--days', type=int, default=7, help='Number of days of history to analyze')
    parser.add_argument('--output', default='logs/diagnostics/reports',
                      help='Output directory for visualizations')
    args = parser.parse_args()
    
    visualizer = DiagnosticsVisualizer()
    data = visualizer.load_diagnostic_data(args.days)
    
    if not data:
        print("No diagnostic data found for the specified period")
        return
        
    os.makedirs(args.output, exist_ok=True)
    report_path = visualizer.generate_report(data, args.output)
    print(f"\nReport generated: {report_path}")

if __name__ == "__main__":
    main()

