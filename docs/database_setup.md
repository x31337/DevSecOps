# Database Setup and Configuration

## Overview
This document covers the database setup and configuration for the VS Code Insiders Extensions project. The project supports two database implementations:
1. SQLite (default) - Used for local development and extension management
2. Prisma with PostgreSQL - Optional setup for advanced use cases and cloud deployment

## SQLite Setup (Default)
The project uses SQLite by default for storing extension metadata. This implementation is handled automatically by the provided scripts and requires no additional setup.

### Default Database Location
- Database file: `db/extension_inventory.db`
- Created automatically by `create_extension_db.py`

## Prisma Setup (Optional)
For advanced use cases requiring PostgreSQL support, follow these steps to configure Prisma:

### Prerequisites
- Prisma must be installed in your project
- A `schema.prisma` file must be present
- If not set up, follow our Quickstart guide first, then return here

### Configure Database Access
1. Create or modify your project's `.env` file at the root:

```env
DATABASE_URL="prisma+postgres://accelerate.prisma-data.net/?api_key=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGlfa2V5IjoiMDFKVzI2V1EwQk1URUc2MFlaVDRWMkFUNVkiLCJ0ZW5hbnRfaWQiOiIyMjg3ZTI1MWUyZDdiNGM1ZjNmYTVmNzQ0YmI4MGNjYjI2ZWU2YmE5YWJiMTIzZjk5YWQ5MWNmYWNhZGIyZDA0IiwiaW50ZXJuYWxfc2VjcmV0IjoiYTg5YWYxYjgtODg1NS00Y2I3LTgwZDQtMjMxYzAyNzdlNDA5In0.BgkCjCfV23lv0k9t28T3LZBZdvNTaiqYf7iK5iN8FAo"
```

2. Make sure your credentials are securely stored and never committed to version control.

### Database Migration
Run the following command to migrate your database with the structure outlined in your schema.prisma file:

```bash
npm run db:migrate
```

### Migration Options

The migration script provides several options for flexibility and control:

```bash
# Basic migration (interactive)
npm run db:migrate

# Force migration without confirmation
npm run db:migrate -- --force

# Specify database type explicitly
npm run db:migrate -- --type postgres
npm run db:migrate -- --type sqlite

# Preview changes without executing (dry run)
npm run db:migrate -- --dry-run

# Enable verbose logging
npm run db:migrate -- --verbose
```

Additional flags:
- `--force` or `-f`: Skip confirmation prompts
- `--type` or `-t`: Force specific database type (sqlite/postgres)
- `--verbose` or `-v`: Show detailed logging information
- `--dry-run` or `-d`: Preview changes without making them

For help with additional options:
```bash
./scripts/migrate_database.py --help
```

### Migration Logs
Migration logs are automatically saved in the `logs` directory with timestamps:
```
logs/db_migration_YYYYMMDD_HHMMSS.log
```

These logs contain detailed information about the migration process and any errors that may have occurred.

### Install Prisma Accelerate Client Extension
Prisma Postgres is powered by Prisma Accelerate, providing scalable connection pooling and built-in global caching.

1. Install required packages:
```bash
npm install prisma @prisma/client@latest @prisma/extension-accelerate
```

2. Generate Prisma Client:
```bash
npx prisma generate --no-engine
```

3. Configure Prisma Client with Accelerate:
```typescript
import { PrismaClient } from '@prisma/client/edge'
import { withAccelerate } from '@prisma/extension-accelerate'

const prisma = new PrismaClient().$extends(withAccelerate())
```

### Third-Party Database Editors
To connect to your Prisma Postgres instance using database editors like pgAdmin, TablePlus, or Postico:

1. Install the tunnel package:
```bash
npm install @prisma/ppg-tunnel
```

2. Follow the connection instructions provided by your database editor using the connection details from your DATABASE_URL.

## Additional Resources
- [Prisma Documentation](https://www.prisma.io/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs)
- [Database Schema Reference](./database_schema.md)

