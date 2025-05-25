#!/usr/bin/env python3

import os
import sys
import time
import sqlite3
import logging
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Database monitoring tool for VS Code Insiders Extensions'
    )
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=300,
        help='Check interval in seconds (default: 300)'
    )
    parser.add_argument(
        '--notify', '-n',
        action='store_true',
        help='Enable desktop notifications for issues'
    )
    parser.add_argument(
        '--log-dir',
        default='logs',
        help='Directory for log files (default: logs)'
    )
    return parser.parse_args()

def setup_logging(log_dir):
    """Configure logging for database monitoring."""
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"db_monitor_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_file

def send_notification(title, message):
    """Send desktop notification."""
    try:
        # Try using notify-send (Linux)
        subprocess.run(['notify-send', title, message])
    except FileNotFoundError:
        try:
            # Try using osascript (macOS)
            apple_script = f'display notification "{message}" with title "{title}"'
            subprocess.run(['osascript', '-e', apple_script])
        except FileNotFoundError:
            # Fall back to console output
            print(f"\n{title}: {message}")

def check_database_health():
    """Check database health and return status."""
    issues = []
    
    # Check SQLite
    db_path = os.path.join('db', 'extension_inventory.db')
    if not os.path.exists(db_path):
        issues.append("SQLite database file missing")
    else:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {table[0] for table in cursor.fetchall()}
            if not {'extensions', 'categories'}.issubset(tables):
                issues.append("Missing required tables")
            
            # Check records
            cursor.execute("SELECT COUNT(*) FROM extensions")
            if cursor.fetchone()[0] == 0:
                issues.append("Extensions table is empty")
            
            conn.close()
        except sqlite3.Error as e:
            issues.append(f"SQLite error: {str(e)}")
    
    # Check PostgreSQL if configured
    if os.path.exists('.env'):
        try:
            result = subprocess.run(
                ['npx', 'prisma', 'db pull'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                issues.append("PostgreSQL connection failed")
        except Exception as e:
            issues.append(f"PostgreSQL error: {str(e)}")
    
    return issues

def main():
    """Main monitoring loop."""
    args = parse_arguments()
    log_file = setup_logging(args.log_dir)
    
    print(f"Starting database monitoring (interval: {args.interval}s)")
    print(f"Log file: {log_file}")
    
    try:
        while True:
            issues = check_database_health()
            
            if issues:
                logging.warning("Database issues detected:")
                for issue in issues:
                    logging.warning(f"- {issue}")
                    
                if args.notify:
                    send_notification(
                        "Database Issue Detected",
                        "\n".join(issues)
                    )
            else:
                logging.info("Database health check passed")
            
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

