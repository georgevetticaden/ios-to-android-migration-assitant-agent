# Database Module

This module manages the DuckDB database for the iOS to Android migration system.

## Structure

```
database/
├── schemas/           # Database schema definitions
│   └── migration_schema.sql
├── scripts/          # Database management scripts
│   ├── initialize_database.py
│   └── reset_database.py
├── tests/            # Database tests
│   └── test_database.py
├── models/           # Data models (if needed)
└── migration_db.py   # Core database interface
```

## Schema

The schema uses a simplified approach with 7 tables (no schema prefixes):

1. **migration_status** - Core migration tracking
2. **family_members** - Family member details with emails
3. **photo_transfer** - Photo migration progress
4. **app_setup** - WhatsApp, Maps, Venmo configuration
5. **family_app_adoption** - Individual app status per family member
6. **daily_progress** - Day-by-day snapshots
7. **venmo_setup** - Teen card tracking

## Usage

### Initialize Database
```bash
python3 shared/database/scripts/initialize_database.py
```

### Run Tests
```bash
python3 shared/database/tests/test_database.py
```

### Reset Database
```bash
python3 shared/database/scripts/reset_database.py
```

### Database Location
The database is stored at: `~/.ios_android_migration/migration.db`

## Key Features

- **No schema complexity** - Direct table creation in DuckDB
- **Email-based coordination** - Family members have emails for invitations
- **Day-aware logic** - Photos visible Day 4, Venmo cards Day 5
- **Constraint enforcement** - CHECK and Foreign Key constraints
- **Useful views** - migration_summary, family_app_status, active_migration

## Testing

All 9 tests should pass:
- Table existence
- Migration initialization
- Family member management
- Photo transfer tracking
- App setup (WhatsApp, Maps, Venmo)
- Family app adoption
- Venmo teen setup
- View functionality
- Constraint enforcement

## Notes

- IDs use prefixes: MIG- for migrations, TRF- for transfers
- Test data uses high IDs (1000+) to avoid conflicts
- Database supports the 7-day demo flow