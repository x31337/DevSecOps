#!/usr/bin/env python3

import os
import sys
import sqlite3
import logging
import subprocess
from datetime import datetime
from pathlib import Path

def setup_logging():
    """Configure logging for database health checks."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"db_healthcheck_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_file

def check_sqlite():
    """Perform SQLite database health checks."""
    db_path = os.path.join('db', 'extension_inventory.db')
    
    if not os.path.exists(db_path):
        logging.error(f"SQLite database not found at: {db_path}")
        return False
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        expected_tables = {'extensions', 'categories'}
        actual_tables = {table[0] for table in tables}
        
        if not expected_tables.issubset(actual_tables):
            missing = expected_tables - actual_tables
            logging.error(f"Missing tables: {missing}")
            return False
            
        # Check extension count
        cursor.execute("SELECT COUNT(*) FROM extensions")
        ext_count = cursor.fetchone()[0]
        logging.info(f"Extensions table contains {ext_count} records")
        
        # Check category count
        cursor.execute("SELECT COUNT(*) FROM categories")
        cat_count = cursor.fetchone()[0]
        logging.info(f"Categories table contains {cat_count} records")
        
        # Verify category statistics
        cursor.execute("""
            SELECT c.count, (SELECT COUNT(*) FROM extensions e WHERE e.category = c.name)
            FROM categories c
        """)
        for stored_count, actual_count in cursor.fetchall():
            if stored_count != actual_count:
                logging.warning(f"Category count mismatch: stored={stored_count}, actual={actual_count}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        logging.error(f"SQLite error: {str(e)}")
        return False

def check_postgres():
    """Perform PostgreSQL/Prisma database health checks."""
    if not os.path.exists('.env'):
        logging.warning("No .env file found for PostgreSQL configuration")
        return False
        
    try:
        # Check Prisma installation
        if not os.path.exists('node_modules/.bin/prisma'):
            logging.error("Prisma not installed")
            return False
            
        # Check database connection
        result = subprocess.run(
            ['npx', 'prisma', 'db pull'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logging.error(f"Prisma connection failed: {result.stderr}")
            return False
            
        logging.info("PostgreSQL connection successful")
        return True
        
    except Exception as e:
        logging.error(f"PostgreSQL check failed: {str(e)}")
        return False

def check_file_permissions():
    """Check file permissions and ownership."""
    db_dir = "db"
    if os.path.exists(db_dir):
        mode = os.stat(db_dir).st_mode
        if not mode & 0o200:  # Write permission
            logging.warning(f"Warning: No write permission on {db_dir}")
    
    if os.path.exists('db/extension_inventory.db'):
        mode = os.stat('db/extension_inventory.db').st_mode
        if not mode & 0o200:  # Write permission
            logging.warning("Warning: No write permission on database file")

def main():
    """Run database health checks."""
    log_file = setup_logging()
    logging.info("Starting database health check...")
    
    try:
        # Check file permissions
        check_file_permissions()
        
        # Check SQLite
        logging.info("Checking SQLite database...")
        sqlite_ok = check_sqlite()
        
        # Check PostgreSQL if configured
        logging.info("Checking PostgreSQL configuration...")
        postgres_ok = check_postgres()
        
        # Summary
        print("\nDatabase Health Check Summary:")
        print(f"SQLite Status: {'✓ OK' if sqlite_ok else '✗ Issues found'}")
        print(f"PostgreSQL Status: {'✓ OK' if postgres_ok else '✗ Issues found'}")
        print(f"\nDetailed log available at: {log_file}")
        
        if not (sqlite_ok or postgres_ok):
            sys.exit(1)
            
    except KeyboardInterrupt:
        logging.warning("Health check interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error during health check: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

