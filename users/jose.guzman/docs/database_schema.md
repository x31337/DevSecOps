# Database Schema Reference

This document provides a detailed reference of the database schema used in the VS Code Insiders Extensions project. The schema is implemented in both SQLite and PostgreSQL (via Prisma) with identical structure.

## Core Tables

### Extensions Table

Stores information about individual VS Code extensions.

#### Schema Definition

```sql
-- SQLite
CREATE TABLE extensions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    publisher     TEXT NOT NULL,
    name          TEXT NOT NULL,
    display_name  TEXT NOT NULL,
    version       TEXT NOT NULL,
    description   TEXT,
    category      TEXT NOT NULL,
    size          INTEGER NOT NULL,
    file_path     TEXT NOT NULL,
    vscode_version TEXT DEFAULT '^1.99.0',
    last_updated   TEXT NOT NULL
);

-- Prisma/PostgreSQL
model Extension {
    id            Int      @id @default(autoincrement())
    publisher     String
    name          String
    displayName   String
    version       String
    description   String?
    category      String
    size          Int
    filePath      String
    vscodeVersion String   @default("^1.99.0")
    lastUpdated   DateTime @default(now())
}
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique identifier for the extension |
| publisher | String | Extension publisher name |
| name | String | Extension name |
| displayName | String | Display name of the extension |
| version | String | Extension version |
| description | String (optional) | Extension description |
| category | String | Category classification |
| size | Integer | Size in bytes |
| filePath | String | Path to the VSIX file |
| vscodeVersion | String | Compatible VS Code version |
| lastUpdated | DateTime | Last update timestamp |

### Categories Table

Stores aggregated information about extension categories.

#### Schema Definition

```sql
-- SQLite
CREATE TABLE categories (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT UNIQUE NOT NULL,
    count     INTEGER DEFAULT 0,
    total_size INTEGER DEFAULT 0
);

-- Prisma/PostgreSQL
model Category {
    id        Int      @id @default(autoincrement())
    name      String   @unique
    count     Int      @default(0)
    totalSize Int      @default(0)
}
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Unique identifier for the category |
| name | String | Category name (unique) |
| count | Integer | Number of extensions in category |
| totalSize | Integer | Total size of all extensions in category |

## Indexing and Performance

### SQLite Indexes
The SQLite implementation automatically creates indexes for:
- Primary keys (id fields)
- Unique constraints (category name)

### PostgreSQL Indexes
Prisma automatically manages indexes for:
- Primary keys (@id fields)
- Unique constraints (@unique fields)

## Data Integrity

### Foreign Key Relationships
- The `category` field in the Extensions table references the `name` field in the Categories table
- This relationship is maintained at the application level rather than through database constraints

### Constraints
- Primary keys are auto-incrementing integers
- Category names must be unique
- All size values must be non-negative
- Required fields are enforced as NOT NULL

## Migrations

### SQLite
SQLite migrations are handled through the `migrate_database.py` script, which ensures table structure is consistent.

### PostgreSQL/Prisma
Prisma migrations are managed through:
```bash
npm run db:migrate
```

For detailed migration instructions, see [Database Setup](database_setup.md).

## Best Practices

1. Always use the provided scripts for database operations
2. Back up data before major migrations
3. Use transactions for bulk operations
4. Monitor the size of the Extensions table
5. Regularly update category statistics

## Schema Updates

When updating the schema:
1. Update both SQLite and Prisma definitions
2. Create appropriate migrations
3. Update related documentation
4. Test both implementations
5. Backup existing data

For implementation details, see the source code in `scripts/create_extension_db.py` and `schema.prisma`.

