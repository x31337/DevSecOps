#!/usr/bin/env python3

import os
import sys
import time
import curses
import sqlite3
import logging
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

class DatabaseDashboard:
    def __init__(self, stdscr, config_path='config/monitor.conf'):
        self.stdscr = stdscr
        self.load_config(config_path)
        self.setup_colors()
        self.last_check = None
        self.error_history = []
        self.metrics_history = []  # Store historical metrics
        self.max_history = 1000    # Keep last 1000 measurements
        curses.curs_set(0)  # Hide cursor
        
    def load_config(self, config_path):
        """Load configuration from file."""
        self.config = {
            'monitor_interval': 300,
            'sqlite_db_path': 'db/extension_inventory.db',
            'postgres_config_path': '.env'
        }
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        self.config[key.lower()] = value.strip('"')
    
    def setup_colors(self):
        """Initialize color pairs."""
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Success
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)    # Error
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Warning
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Info
    
    def get_sqlite_metrics(self):
        """Get SQLite database metrics."""
        metrics = {
            'status': 'ERROR',
            'extensions': 0,
            'categories': 0,
            'size': 0,
            'last_updated': None
        }
        
        try:
            db_path = self.config['sqlite_db_path']
            if os.path.exists(db_path):
                metrics['size'] = os.path.getsize(db_path)
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Get extension count
                cursor.execute("SELECT COUNT(*) FROM extensions")
                metrics['extensions'] = cursor.fetchone()[0]
                
                # Get category count
                cursor.execute("SELECT COUNT(*) FROM categories")
                metrics['categories'] = cursor.fetchone()[0]
                
                # Get last update
                cursor.execute("SELECT MAX(last_updated) FROM extensions")
                metrics['last_updated'] = cursor.fetchone()[0]
                
                metrics['status'] = 'OK'
                conn.close()
        except Exception as e:
            metrics['status'] = f'ERROR: {str(e)}'
        
        return metrics
    
    def get_postgres_metrics(self):
        """Get PostgreSQL database metrics."""
        metrics = {
            'status': 'NOT CONFIGURED',
            'connected': False,
            'version': None
        }
        
        if os.path.exists(self.config['postgres_config_path']):
            try:
                import subprocess
                result = subprocess.run(
                    ['npx', 'prisma', 'db pull'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    metrics['status'] = 'OK'
                    metrics['connected'] = True
            except Exception as e:
                metrics['status'] = f'ERROR: {str(e)}'
        
        return metrics
    
    def get_performance_metrics(self):
        """Get database performance metrics."""
        metrics = {
            'query_time': 0,
            'connection_time': 0,
            'total_size': 0,
            'memory_usage': 0
        }
        
        start_time = time.time()
        try:
            # SQLite performance check
            conn = sqlite3.connect(self.config['sqlite_db_path'])
            metrics['connection_time'] = time.time() - start_time
            
            query_start = time.time()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM extensions")
            cursor.execute("SELECT COUNT(*) FROM categories")
            metrics['query_time'] = time.time() - query_start
            
            # Get total database size
            metrics['total_size'] = os.path.getsize(self.config['sqlite_db_path'])
            
            # Get memory usage
            import psutil
            process = psutil.Process()
            metrics['memory_usage'] = process.memory_info().rss
            
            conn.close()
        except Exception:
            pass
            
        return metrics
    
    def add_error(self, error_msg):
        """Add error to history."""
        timestamp = datetime.now()
        self.error_history.append((timestamp, error_msg))
        # Keep only last 5 errors
        self.error_history = self.error_history[-5:]
    
    def save_metrics(self):
        """Save current metrics to a log file."""
        try:
            # Create metrics directory if it doesn't exist
            os.makedirs('metrics', exist_ok=True)
            
            # Get current metrics
            current_metrics = {
                'timestamp': datetime.now().isoformat(),
                'sqlite': self.get_sqlite_metrics(),
                'postgres': self.get_postgres_metrics(),
                'performance': self.get_performance_metrics()
            }
            
            # Add to history
            self.metrics_history.append(current_metrics)
            self.metrics_history = self.metrics_history[-self.max_history:]
            
            # Save to daily log file
            filename = f"metrics/db_metrics_{datetime.now().strftime('%Y%m%d')}.json"
            
            # Load existing metrics if file exists
            existing_metrics = []
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    existing_metrics = json.load(f)
            
            # Append new metrics
            existing_metrics.append(current_metrics)
            
            # Save updated metrics
            with open(filename, 'w') as f:
                json.dump(existing_metrics, f, indent=2)
            
            # Generate summary report
            self.generate_summary_report()
            
            return True
        except Exception as e:
            self.add_error(f"Failed to save metrics: {str(e)}")
            return False
    
    def generate_summary_report(self):
        """Generate a summary report of metrics."""
        try:
            report_file = f"metrics/summary_{datetime.now().strftime('%Y%m%d')}.txt"
            
            with open(report_file, 'w') as f:
                f.write("Database Metrics Summary Report\n")
                f.write("=" * 30 + "\n\n")
                
                # Calculate statistics
                sqlite_sizes = [m['sqlite']['size'] for m in self.metrics_history]
                query_times = [m['performance']['query_time'] for m in self.metrics_history]
                
                f.write(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Metrics Collected: {len(self.metrics_history)}\n\n")
                
                f.write("SQLite Statistics:\n")
                f.write(f"- Average Size: {self.format_size(sum(sqlite_sizes)/len(sqlite_sizes))}\n")
                f.write(f"- Max Size: {self.format_size(max(sqlite_sizes))}\n")
                f.write(f"- Min Size: {self.format_size(min(sqlite_sizes))}\n\n")
                
                f.write("Performance Statistics:\n")
                f.write(f"- Average Query Time: {sum(query_times)/len(query_times)*1000:.2f}ms\n")
                f.write(f"- Max Query Time: {max(query_times)*1000:.2f}ms\n")
                f.write(f"- Min Query Time: {min(query_times)*1000:.2f}ms\n")
                
        except Exception as e:
            self.add_error(f"Failed to generate summary report: {str(e)}")
    
    def format_size(self, size_bytes):
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def draw_header(self, y, x):
        """Draw dashboard header."""
        self.stdscr.addstr(y, x, "VS Code Extensions Database Monitor", curses.A_BOLD)
        self.stdscr.addstr(y + 1, x, "=" * 50)
        if self.last_check:
            self.stdscr.addstr(y + 2, x, f"Last check: {self.last_check.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def draw_sqlite_panel(self, y, x):
        """Draw SQLite metrics panel."""
        metrics = self.get_sqlite_metrics()
        
        self.stdscr.addstr(y, x, "SQLite Database", curses.A_BOLD)
        self.stdscr.addstr(y + 1, x, "-" * 30)
        
        status_color = curses.color_pair(1) if metrics['status'] == 'OK' else curses.color_pair(2)
        self.stdscr.addstr(y + 2, x, f"Status: ", curses.A_BOLD)
        self.stdscr.addstr(metrics['status'], status_color)
        
        self.stdscr.addstr(y + 3, x, f"Extensions: {metrics['extensions']}")
        self.stdscr.addstr(y + 4, x, f"Categories: {metrics['categories']}")
        self.stdscr.addstr(y + 5, x, f"Database Size: {self.format_size(metrics['size'])}")
        if metrics['last_updated']:
            self.stdscr.addstr(y + 6, x, f"Last Updated: {metrics['last_updated']}")
    
    def draw_postgres_panel(self, y, x):
        """Draw PostgreSQL metrics panel."""
        metrics = self.get_postgres_metrics()
        
        self.stdscr.addstr(y, x, "PostgreSQL Database", curses.A_BOLD)
        self.stdscr.addstr(y + 1, x, "-" * 30)
        
        status_color = curses.color_pair(1) if metrics['status'] == 'OK' else curses.color_pair(3)
        self.stdscr.addstr(y + 2, x, f"Status: ", curses.A_BOLD)
        self.stdscr.addstr(metrics['status'], status_color)
        
        self.stdscr.addstr(y + 3, x, f"Connected: {metrics['connected']}")
        if metrics['version']:
            self.stdscr.addstr(y + 4, x, f"Version: {metrics['version']}")
    
    def draw_performance_panel(self, y, x):
        """Draw performance metrics panel."""
        metrics = self.get_performance_metrics()
        
        self.stdscr.addstr(y, x, "Performance Metrics", curses.A_BOLD)
        self.stdscr.addstr(y + 1, x, "-" * 30)
        
        self.stdscr.addstr(y + 2, x, f"Query Time: {metrics['query_time']*1000:.2f}ms")
        self.stdscr.addstr(y + 3, x, f"Connection Time: {metrics['connection_time']*1000:.2f}ms")
        self.stdscr.addstr(y + 4, x, f"Memory Usage: {self.format_size(metrics['memory_usage'])}")
    
    def draw_error_panel(self, y, x):
        """Draw error history panel."""
        self.stdscr.addstr(y, x, "Recent Errors", curses.A_BOLD)
        self.stdscr.addstr(y + 1, x, "-" * 30)
        
        if not self.error_history:
            self.stdscr.addstr(y + 2, x, "No recent errors", curses.color_pair(1))
        else:
            for i, (timestamp, error) in enumerate(self.error_history):
                if i < 5:  # Show only last 5 errors
                    time_str = timestamp.strftime("%H:%M:%S")
                    self.stdscr.addstr(y + 2 + i, x, f"{time_str}: {error[:40]}", curses.color_pair(2))
    
    def draw_footer(self, y, x):
        """Draw dashboard footer."""
        self.stdscr.addstr(y, x, "Commands: ", curses.A_BOLD)
        self.stdscr.addstr("q", curses.color_pair(4))
        self.stdscr.addstr(" Quit | ")
        self.stdscr.addstr("r", curses.color_pair(4))
        self.stdscr.addstr(" Refresh | ")
        self.stdscr.addstr("c", curses.color_pair(4))
        self.stdscr.addstr(" Clear Errors | ")
        self.stdscr.addstr("s", curses.color_pair(4))
        self.stdscr.addstr(" Save Metrics")
    
    def draw_metrics_panel(self, y, x):
        """Draw metrics history panel."""
        if not self.metrics_history:
            return
            
        self.stdscr.addstr(y, x, "Metrics History", curses.A_BOLD)
        self.stdscr.addstr(y + 1, x, "-" * 30)
        
        # Show trend indicators
        latest = self.metrics_history[-1]
        if len(self.metrics_history) > 1:
            previous = self.metrics_history[-2]
            
            query_trend = "↑" if latest['performance']['query_time'] > previous['performance']['query_time'] else "↓"
            size_trend = "↑" if latest['sqlite']['size'] > previous['sqlite']['size'] else "↓"
            
            self.stdscr.addstr(y + 2, x, f"Query Time: {query_trend} ", curses.A_BOLD)
            self.stdscr.addstr(y + 3, x, f"DB Size: {size_trend} ", curses.A_BOLD)
    
    def update(self):
        """Update dashboard display."""
        self.stdscr.clear()
        self.last_check = datetime.now()
        
        # Draw components
        self.draw_header(0, 2)
        self.draw_sqlite_panel(4, 2)
        self.draw_postgres_panel(12, 2)
        self.draw_performance_panel(4, 40)  # New position for performance panel
        self.draw_error_panel(12, 40)       # New position for error panel
        self.draw_metrics_panel(12, 80)     # Add metrics history panel
        self.draw_footer(20, 2)
        
        self.stdscr.refresh()

def main(stdscr):
    """Main dashboard function."""
    dashboard = DatabaseDashboard(stdscr)
    last_save = datetime.now()
    save_interval = timedelta(minutes=5)  # Save metrics every 5 minutes
    
    while True:
        dashboard.update()
        
        # Save metrics periodically
        if datetime.now() - last_save > save_interval:
            dashboard.save_metrics()
            last_save = datetime.now()
        
        # Check for input (with timeout)
        try:
            key = stdscr.getch()
            if key == ord('q'):
                break
            elif key == ord('r'):
                continue
            elif key == ord('c'):
                dashboard.error_history.clear()  # Clear error history
            elif key == ord('s'):
                if dashboard.save_metrics():
                    logging.info("Dashboard metrics exported successfully")
            elif key == ord('h'):
                # Toggle help display
                pass
        except curses.error:
            pass
        
        time.sleep(5)  # Update every 5 seconds

if __name__ == "__main__":
    curses.wrapper(main)

