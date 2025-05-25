# Database Troubleshooting Guide

This guide helps resolve common database-related issues in the VS Code Insiders Extensions project.

## Common Issues

### SQLite Issues

#### Database Locked
```
Error: database is locked
```
**Solution:**
1. Ensure no other processes are accessing the database
2. Check for hanging processes:
   ```bash
   lsof db/extension_inventory.db
   ```
3. If needed, close the database connection:
   ```bash
   npm run db:reset
   ```

#### Missing Tables
```
Error: no such table: extensions
```
**Solution:**
1. Run the migration script:
   ```bash
   npm run db:migrate
   ```
2. If issue persists, try forcing SQLite:
   ```bash
   npm run db:migrate -- --type sqlite --force
   ```

### PostgreSQL/Prisma Issues

#### Connection Failed
```
Error: P1001: Can't reach database server
```
**Solution:**
1. Verify DATABASE_URL in .env
2. Check database server status
3. Test connection:
   ```bash
   npx prisma db pull
   ```

#### Schema Mismatch
```
Error: P2022: The table `Extension` does not exist in the current database
```
**Solution:**
1. Reset Prisma schema:
   ```bash
   npm run db:migrate:reset
   npm run db:migrate
   ```

#### Migration Failed
```
Error: P3014: Migration failed
```
**Solution:**
1. Check migration logs in `logs/`
2. Reset migration state:
   ```bash
   npm run db:reset
   npm run db:migrate
   ```

## Verification Steps

### Database Integrity Check

1. Check SQLite database:
   ```bash
   sqlite3 db/extension_inventory.db ".tables"
   sqlite3 db/extension_inventory.db "SELECT count(*) FROM extensions;"
   ```

2. Check PostgreSQL database:
   ```bash
   npx prisma studio
   ```

### Log Analysis

Check recent logs in `logs/` directory:
```bash
tail -f logs/db_migration_*.log
```

## Prevention Tips

1. Always use provided scripts for database operations
2. Back up data before migrations
3. Check logs for warnings
4. Keep Prisma CLI up to date
5. Monitor database size

## Recovery Steps

### SQLite Recovery

1. Backup current database:
   ```bash
   cp db/extension_inventory.db db/extension_inventory.db.backup
   ```

2. Recreate database:
   ```bash
   rm db/extension_inventory.db
   npm run db:migrate -- --type sqlite
   ```

### PostgreSQL Recovery

1. Reset Prisma state:
   ```bash
   npm run db:reset
   ```

2. Regenerate client:
   ```bash
   npm run db:generate
   ```

3. Remigrate database:
   ```bash
   npm run db:migrate
   ```

## Getting Help

If issues persist:
1. Check full logs in `logs/` directory
2. Review [Database Setup Guide](database_setup.md)
3. Verify [Schema Reference](database_schema.md)
4. Create an issue with:
   - Error message
   - Log contents
   - Database type
   - Recent operations performed

## Advanced Troubleshooting

### Database Diagnostics

Run the diagnostic script:
```bash
npm run db:migrate -- --verbose
```

### Performance Issues

1. Check database size:
   ```bash
   ls -lh db/extension_inventory.db
   ```

2. Monitor query performance:
   ```bash
   npm run db:studio
   ```

3. Review indexing:
   - See [Schema Reference](database_schema.md#indexing-and-performance)

Remember to always backup your data before attempting any recovery procedures.

