#!/usr/bin/env python3

import os
import sys
import sqlite3
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Configure logging
def setup_logging():
    """Configure logging for database migrations."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"db_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_file

def check_env():
    """Check if environment is properly configured."""
    if not os.path.exists('.env'):
        logging.warning(".env file not found. Using default SQLite configuration.")
        return 'sqlite'
    
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    if 'postgresql' in line or 'postgres' in line:
                        logging.info("PostgreSQL configuration detected.")
                        return 'postgres'
    except Exception as e:
        logging.error(f"Error reading .env file: {str(e)}")
        return 'sqlite'
    
    logging.info("No PostgreSQL configuration found. Using SQLite.")
    return 'sqlite'

def migrate_sqlite():
    """Handle SQLite database migration."""
    db_path = os.path.join('db', 'extension_inventory.db')
    
    try:
        # Ensure db directory exists
        os.makedirs('db', exist_ok=True)
        logging.info(f"Using SQLite database at: {db_path}")
        
        # Create new database connection
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        logging.info("Creating/updating SQLite tables...")
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS extensions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            publisher TEXT,
            name TEXT,
            display_name TEXT,
            version TEXT,
            description TEXT,
            category TEXT,
            size INTEGER,
            file_path TEXT,
            vscode_version TEXT,
            last_updated TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            count INTEGER DEFAULT 0,
            total_size INTEGER DEFAULT 0
        )
        ''')
        
        conn.commit()
        conn.close()
        
        logging.info("SQLite database migration completed successfully.")
        
    except sqlite3.Error as e:
        logging.error(f"SQLite error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error during SQLite migration: {str(e)}")
        sys.exit(1)

def migrate_postgres():
    """Handle PostgreSQL database migration using Prisma."""
    try:
        logging.info("Starting PostgreSQL migration using Prisma...")
        
        # Verify Prisma installation
        if not os.path.exists('node_modules/.bin/prisma'):
            logging.error("Prisma not found. Please run 'npm install' first.")
            sys.exit(1)
        
        # Run Prisma migration
        result = subprocess.run(
            ['npx', 'prisma', 'migrate', 'dev'], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            logging.info("PostgreSQL database migration completed successfully.")
        else:
            logging.error("Error during PostgreSQL migration:")
            logging.error(result.stderr)
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        logging.error(f"Prisma command failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error during PostgreSQL migration: {str(e)}")
        sys.exit(1)

def main():
    """Main function to handle database migrations."""
    log_file = setup_logging()
    logging.info("Starting database migration...")
    
    try:
        # Check database type from environment
        db_type = check_env()
        
        if db_type == 'postgres':
            migrate_postgres()
        else:
            migrate_sqlite()
        
        logging.info("\nMigration completed successfully!")
        print("\nNext steps:")
        print("1. Run 'npm start' to populate the database with extension data")
        print("2. Check the logs directory for any warnings or errors")
        print(f"3. View detailed migration log at: {log_file}")
        print("4. Use 'npm run db:studio' to view the database (PostgreSQL only)")
        
    except KeyboardInterrupt:
        logging.warning("Migration interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

