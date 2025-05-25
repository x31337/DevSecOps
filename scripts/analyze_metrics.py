#!/usr/bin/env python3

import os
import json
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Analyze database metrics and generate reports'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to analyze (default: 7)'
    )
    parser.add_argument(
        '--output',
        default='metrics/reports',
        help='Output directory for reports'
    )
    parser.add_argument(
        '--format',
        choices=['html', 'pdf', 'text'],
        default='html',
        help='Report format (default: html)'
    )
    return parser.parse_args()

def load_metrics(days):
    """Load metrics from the last N days."""
    metrics = []
    today = datetime.now()
    
    for i in range(days):
        date = today - timedelta(days=i)
        filename = f"metrics/db_metrics_{date.strftime('%Y%m%d')}.json"
        
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                day_metrics = json.load(f)
                metrics.extend(day_metrics)
    
    return metrics

def create_dataframe(metrics):
    """Convert metrics to pandas DataFrame."""
    data = []
    
    for metric in metrics:
        row = {
            'timestamp': datetime.fromisoformat(metric['timestamp']),
            'sqlite_size': metric['sqlite']['size'],
            'sqlite_extensions': metric['sqlite']['extensions'],
            'sqlite_categories': metric['sqlite']['categories'],
            'sqlite_status': metric['sqlite']['status'] == 'OK',
            'postgres_connected': metric['postgres']['connected'],
            'query_time': metric['performance']['query_time'],
            'connection_time': metric['performance']['connection_time'],
            'memory_usage': metric['performance']['memory_usage']
        }
        data.append(row)
    
    return pd.DataFrame(data)

def generate_plots(df, output_dir):
    """Generate analysis plots."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Database size over time
    plt.figure(figsize=(10, 6))
    plt.plot(df['timestamp'], df['sqlite_size'] / 1024 / 1024, 'b-')
    plt.title('Database Size Over Time')
    plt.xlabel('Time')
    plt.ylabel('Size (MB)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'size_trend.png'))
    plt.close()
    
    # Query performance
    plt.figure(figsize=(10, 6))
    plt.plot(df['timestamp'], df['query_time'] * 1000, 'r-', label='Query Time')
    plt.plot(df['timestamp'], df['connection_time'] * 1000, 'g-', label='Connection Time')
    plt.title('Database Performance')
    plt.xlabel('Time')
    plt.ylabel('Time (ms)')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'performance.png'))
    plt.close()
    
    # Memory usage
    plt.figure(figsize=(10, 6))
    plt.plot(df['timestamp'], df['memory_usage'] / 1024 / 1024, 'g-')
    plt.title('Memory Usage')
    plt.xlabel('Time')
    plt.ylabel('Memory (MB)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'memory.png'))
    plt.close()

def format_text_table(df, width=80):
    """Format DataFrame as fixed-width text table."""
    def format_row(items, widths):
        return '|' + '|'.join(f' {str(item):<{w-2}} ' for item, w in zip(items, widths)) + '|'
    
    columns = ['Timestamp', 'Size (MB)', 'Query (ms)', 'Memory (MB)', 'Status']
    data = [
        [
            row['timestamp'].strftime('%Y-%m-%d %H:%M'),
            f"{row['sqlite_size']/1024/1024:.1f}",
            f"{row['query_time']*1000:.1f}",
            f"{row['memory_usage']/1024/1024:.1f}",
            'OK' if row['sqlite_status'] else 'ERROR'
        ]
        for _, row in df.iterrows()
    ]
    
    # Calculate column widths
    widths = [max(len(str(item)) for item in col) + 4 for col in zip(columns, *data)]
    widths = [min(w, width//len(widths)) for w in widths]  # Limit maximum width
    
    # Generate table
    separator = '+' + '+'.join('-' * w for w in widths) + '+'
    rows = [separator, format_row(columns, widths), separator]
    rows.extend(format_row(row, widths) for row in data)
    rows.append(separator)
    
    return '\n'.join(rows)

def generate_text_report(df, output_dir):
    """Generate text report with metrics analysis."""
    report_path = os.path.join(output_dir, 'report.txt')
    
    with open(report_path, 'w') as f:
        # Write header
        f.write('Database Metrics Analysis Report\n')
        f.write('=' * 30 + '\n\n')
        
        # Summary statistics
        f.write('Summary Statistics\n')
        f.write('-' * 20 + '\n')
        f.write(f"Period: {df['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S')} to {df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Measurements: {len(df)}\n")
        f.write(f"Average Database Size: {df['sqlite_size'].mean()/1024/1024:.2f} MB\n")
        f.write(f"Average Query Time: {df['query_time'].mean()*1000:.2f} ms\n")
        f.write(f"SQLite Uptime: {df['sqlite_status'].mean()*100:.1f}%\n")
        f.write(f"PostgreSQL Uptime: {df['postgres_connected'].mean()*100:.1f}%\n\n")
        
        # Key metrics table
        f.write('Detailed Metrics\n')
        f.write('-' * 20 + '\n')
        f.write(format_text_table(df))
        
        # Performance summary
        f.write('\nPerformance Summary\n')
        f.write('-' * 20 + '\n')
        f.write(f"Peak Memory Usage: {df['memory_usage'].max()/1024/1024:.1f} MB\n")
        f.write(f"Max Query Time: {df['query_time'].max()*1000:.1f} ms\n")
        f.write(f"Max Database Size: {df['sqlite_size'].max()/1024/1024:.1f} MB\n")

def generate_pdf_report(df, output_dir):
    """Generate PDF report with metrics analysis."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
    except ImportError:
        print("reportlab package required for PDF generation. Install with: pip install reportlab")
        return
    
    report_path = os.path.join(output_dir, 'report.pdf')
    doc = SimpleDocTemplate(report_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    story.append(Paragraph("Database Metrics Analysis", styles['Title']))
    story.append(Spacer(1, 12))
    
    # Summary statistics
    story.append(Paragraph("Summary Statistics", styles['Heading1']))
    stats = [
        [f"Period:", f"{df['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S')} to {df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')}"],
        ["Total Measurements:", str(len(df))],
        ["Average Database Size:", f"{df['sqlite_size'].mean()/1024/1024:.2f} MB"],
        ["Average Query Time:", f"{df['query_time'].mean()*1000:.2f} ms"],
        ["SQLite Uptime:", f"{df['sqlite_status'].mean()*100:.1f}%"],
        ["PostgreSQL Uptime:", f"{df['postgres_connected'].mean()*100:.1f}%"]
    ]
    
    t = Table(stats)
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('PADDING', (0, 0), (-1, -1), 6)
    ]))
    story.append(t)
    story.append(Spacer(1, 12))
    
    # Plots
    for plot in ['size_trend.png', 'performance.png', 'memory.png']:
        if os.path.exists(os.path.join(output_dir, plot)):
            img = Image(os.path.join(output_dir, plot), width=6*inch, height=4*inch)
            story.append(img)
            story.append(Spacer(1, 12))
    
    # Build PDF
    doc.build(story)

def generate_html_report(df, output_dir):
    """Generate HTML report with metrics analysis."""
    template = """
    <html>
    <head>
        <title>Database Metrics Analysis</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .metric { margin: 20px 0; padding: 10px; border: 1px solid #ccc; }
            .plot { margin: 20px 0; }
            .summary { background: #f5f5f5; padding: 15px; }
        </style>
    </head>
    <body>
        <h1>Database Metrics Analysis</h1>
        <div class="summary">
            <h2>Summary Statistics</h2>
            <p>Period: {start_date} to {end_date}</p>
            <p>Total Measurements: {total_measurements}</p>
            <p>Average Database Size: {avg_size:.2f} MB</p>
            <p>Average Query Time: {avg_query:.2f} ms</p>
            <p>SQLite Uptime: {sqlite_uptime:.1f}%</p>
            <p>PostgreSQL Uptime: {postgres_uptime:.1f}%</p>
        </div>
        
        <div class="plot">
            <h2>Database Size Trend</h2>
            <img src="size_trend.png" />
        </div>
        
        <div class="plot">
            <h2>Performance Metrics</h2>
            <img src="performance.png" />
        </div>
        
        <div class="plot">
            <h2>Memory Usage</h2>
            <img src="memory.png" />
        </div>
        
        <div class="metric">
            <h2>Key Metrics</h2>
            <pre>{key_metrics}</pre>
        </div>
    </body>
    </html>
    """
    
    # Calculate summary statistics
    stats = {
        'start_date': df['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S'),
        'end_date': df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S'),
        'total_measurements': len(df),
        'avg_size': df['sqlite_size'].mean() / 1024 / 1024,
        'avg_query': df['query_time'].mean() * 1000,
        'sqlite_uptime': df['sqlite_status'].mean() * 100,
        'postgres_uptime': df['postgres_connected'].mean() * 100,
        'key_metrics': df.describe().to_string()
    }
    
    # Generate HTML
    html_content = template.format(**stats)
    
    # Save report
    with open(os.path.join(output_dir, 'report.html'), 'w') as f:
        f.write(html_content)

def analyze_trends(df):
    """Analyze trends and identify potential issues."""
    alerts = []
    
    # Define thresholds
    THRESHOLDS = {
        'query_time': 1.0,      # Alert if query time > 1 second
        'memory_growth': 20,    # Alert if memory grows > 20% in 24h
        'db_growth': 50,        # Alert if DB size grows > 50% in 24h
        'error_rate': 0.1       # Alert if error rate > 10%
    }
    
    # Query time trend
    high_query_times = df[df['query_time'] > THRESHOLDS['query_time']]
    if not high_query_times.empty:
        alerts.append(f"High query times detected: {len(high_query_times)} queries exceeded {THRESHOLDS['query_time']}s")
    
    # Memory usage trend
    if len(df) >= 2:
        memory_growth = (df['memory_usage'].iloc[-1] - df['memory_usage'].iloc[0]) / df['memory_usage'].iloc[0] * 100
        if memory_growth > THRESHOLDS['memory_growth']:
            alerts.append(f"High memory growth: {memory_growth:.1f}% increase")
    
    # Database size trend
    if len(df) >= 2:
        size_growth = (df['sqlite_size'].iloc[-1] - df['sqlite_size'].iloc[0]) / df['sqlite_size'].iloc[0] * 100
        if size_growth > THRESHOLDS['db_growth']:
            alerts.append(f"High database growth: {size_growth:.1f}% increase")
    
    # Error rate analysis
    error_rate = 1 - df['sqlite_status'].mean()
    if error_rate > THRESHOLDS['error_rate']:
        alerts.append(f"High error rate: {error_rate*100:.1f}% of checks failed")
    
    # Performance degradation detection
    if len(df) > 10:
        recent_queries = df['query_time'].tail(5).mean()
        older_queries = df['query_time'].head(5).mean()
        if recent_queries > older_queries * 1.5:  # 50% slower
            alerts.append("Performance degradation detected: Queries are getting slower")
    
    return alerts

def format_recommendations(df, alerts):
    """Generate recommendations based on alerts."""
    recommendations = []
    
    if any('query time' in alert.lower() for alert in alerts):
        recommendations.append("Consider optimizing database queries or adding indexes")
    
    if any('memory' in alert.lower() for alert in alerts):
        recommendations.append("Monitor application memory usage and consider memory optimization")
    
    if any('growth' in alert.lower() for alert in alerts):
        recommendations.append("Review database growth and implement cleanup/archival strategy")
    
    if any('error rate' in alert.lower() for alert in alerts):
        recommendations.append("Investigate cause of frequent errors and implement error handling")
    
    return recommendations

def add_trend_analysis_to_reports(df, output_dir, format='html'):
    """Add trend analysis to existing reports."""
    alerts = analyze_trends(df)
    recommendations = format_recommendations(df, alerts)
    
    if format == 'html':
        # Add to HTML report
        with open(os.path.join(output_dir, 'report.html'), 'r') as f:
            content = f.read()
        
        alert_html = """
        <div class="alerts">
            <h2>Alerts and Recommendations</h2>
            <div class="alert-list">
                <h3>Alerts:</h3>
                <ul>
                    {}
                </ul>
            </div>
            <div class="recommendations">
                <h3>Recommendations:</h3>
                <ul>
                    {}
                </ul>
            </div>
        </div>
        </body>
        """.format(
            '\n'.join(f'<li style="color: red;">{alert}</li>' for alert in alerts) if alerts else '<li>No alerts detected</li>',
            '\n'.join(f'<li>{rec}</li>' for rec in recommendations) if recommendations else '<li>No recommendations at this time</li>'
        )
        
        content = content.replace('</body>', alert_html)
        
        with open(os.path.join(output_dir, 'report.html'), 'w') as f:
            f.write(content)
            
    elif format == 'text':
        # Add to text report
        with open(os.path.join(output_dir, 'report.txt'), 'a') as f:
            f.write('\nAlerts and Recommendations\n')
            f.write('=' * 30 + '\n\n')
            
            if alerts:
                f.write('Alerts:\n')
                for alert in alerts:
                    f.write(f"! {alert}\n")
            else:
                f.write('No alerts detected\n')
                
            f.write('\nRecommendations:\n')
            if recommendations:
                for rec in recommendations:
                    f.write(f"* {rec}\n")
            else:
                f.write('No recommendations at this time\n')
                
    elif format == 'pdf':
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            print("Warning: reportlab package not found, skipping PDF alert updates")
            return
            
        # Since we need to regenerate the PDF, we'll append to it
        report_path = os.path.join(output_dir, 'report_with_alerts.pdf')
        doc = SimpleDocTemplate(report_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title for alerts section
        story.append(Paragraph("Alerts and Recommendations", styles['Heading1']))
        story.append(Spacer(1, 12))
        
        # Add alerts
        if alerts:
            story.append(Paragraph("Alerts", styles['Heading2']))
            for alert in alerts:
                story.append(Paragraph(f"• {alert}", styles['BodyText']))
            story.append(Spacer(1, 12))
        else:
            story.append(Paragraph("No alerts detected", styles['BodyText']))
            story.append(Spacer(1, 12))
        
        # Add recommendations
        if recommendations:
            story.append(Paragraph("Recommendations", styles['Heading2']))
            for rec in recommendations:
                story.append(Paragraph(f"• {rec}", styles['BodyText']))
        else:
            story.append(Paragraph("No recommendations at this time", styles['BodyText']))
        
        # Build PDF
        doc.build(story)
        print(f"Alert report generated: {report_path}")

def main():
    """Main analysis function."""
    args = parse_arguments()
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Load and process metrics
    metrics = load_metrics(args.days)
    if not metrics:
        print("No metrics found for the specified period")
        return
    
    # Create DataFrame
    df = create_dataframe(metrics)
    
    # Generate plots
    generate_plots(df, args.output)
    
    # Generate report in requested format
    if args.format == 'html':
        generate_html_report(df, args.output)
    elif args.format == 'pdf':
        generate_pdf_report(df, args.output)
    elif args.format == 'text':
        generate_text_report(df, args.output)
    
    # Add trend analysis
    add_trend_analysis_to_reports(df, args.output, args.format)
    
    print(f"Analysis complete. Reports available in: {args.output}")

if __name__ == "__main__":
    main()

