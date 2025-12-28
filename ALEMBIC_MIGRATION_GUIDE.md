# Alembic Migration Guide

## Overview

This guide walks through migrating from in-code migrations to Alembic for proper database version control and migration management.

## Why Alembic?

**Current Issues with In-Code Migrations:**
- Hard to version control and track migration history
- Difficult to roll back changes
- No clear migration ordering
- Risk of running migrations out of sequence
- Hard to test migrations in isolation

**Benefits of Alembic:**
- Version-controlled migration files
- Easy rollback with `alembic downgrade`
- Clear migration history with `alembic history`
- Automatic migration generation from model changes
- Industry-standard tool for SQLAlchemy projects

## Installation

### 1. Add Alembic to Requirements

```bash
cd backend
echo "alembic==1.13.1" >> requirements.txt
pip install -r requirements.txt
```

### 2. Initialize Alembic

```bash
cd backend
alembic init alembic
```

This creates:
```
backend/
├── alembic/
│   ├── env.py           # Alembic environment configuration
│   ├── script.py.mako   # Migration template
│   └── versions/        # Migration files go here
└── alembic.ini          # Alembic configuration
```

## Configuration

### 1. Update alembic.ini

Edit `backend/alembic.ini`:

```ini
# Line ~58: Comment out the default sqlalchemy.url
# sqlalchemy.url = driver://user:pass@localhost/dbname

# Alembic will get the URL from env.py instead
```

### 2. Configure env.py

Edit `backend/alembic/env.py`:

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import your models and database config
from models import Base
from config import DATABASE_URL

# this is the Alembic Config object
config = context.config

# Set the database URL from config
config.set_main_option('sqlalchemy.url', DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Detect column type changes
        compare_server_default=True,  # Detect default value changes
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # Detect column type changes
            compare_server_default=True,  # Detect default value changes
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

## Migration Workflow

### 1. Create Initial Migration (Baseline)

```bash
# Generate migration from current models
alembic revision --autogenerate -m "Initial schema"

# Review the generated migration in alembic/versions/
# Edit if needed

# Apply the migration
alembic upgrade head
```

### 2. Making Schema Changes

**Step 1: Update Models**
Edit `backend/models.py` to add/modify/remove columns

**Step 2: Generate Migration**
```bash
alembic revision --autogenerate -m "Add new_column to Game table"
```

**Step 3: Review Migration**
```bash
# Check the generated file in alembic/versions/
cat alembic/versions/xxxx_add_new_column.py
```

**Step 4: Test Migration**
```bash
# Apply migration
alembic upgrade head

# Verify schema
psql $DATABASE_URL -c "\d boardgames"

# Test rollback
alembic downgrade -1
alembic upgrade head
```

**Step 5: Commit**
```bash
git add alembic/versions/xxxx_add_new_column.py
git commit -m "Add new_column to Game model"
```

### 3. Converting Existing In-Code Migrations

Current in-code migrations are in `backend/database.py`. To convert:

**Option A: Keep as baseline**
1. Remove migration code from `database.py`
2. Create initial Alembic migration from current schema
3. Mark as applied: `alembic stamp head`

**Option B: Convert to Alembic migrations**
1. Create individual Alembic migrations for each in-code migration
2. Add version checking to ensure correct order
3. Remove old migration code

Recommended: **Option A** - treat current schema as baseline

## Common Commands

### Check Migration Status
```bash
alembic current              # Show current revision
alembic history              # Show all migrations
alembic history --verbose    # Detailed history
```

### Apply Migrations
```bash
alembic upgrade head         # Apply all pending migrations
alembic upgrade +1           # Apply next migration
alembic upgrade <revision>   # Upgrade to specific revision
```

### Rollback Migrations
```bash
alembic downgrade -1         # Rollback one migration
alembic downgrade <revision> # Downgrade to specific revision
alembic downgrade base       # Rollback all migrations
```

### Generate Migrations
```bash
alembic revision --autogenerate -m "Description"  # Auto-generate from models
alembic revision -m "Description"                  # Create empty migration
```

## Best Practices

### 1. Always Review Auto-Generated Migrations
Alembic's autogenerate is smart but not perfect:
- May not detect renamed columns (sees as drop + add)
- Doesn't detect changed indexes
- Can't detect data migrations

Always review and edit generated migrations.

### 2. Add Data Migrations When Needed
```python
def upgrade():
    # Schema change
    op.add_column('boardgames', sa.Column('new_field', sa.String(50)))

    # Data migration
    op.execute("""
        UPDATE boardgames
        SET new_field = 'default_value'
        WHERE new_field IS NULL
    """)

    # Make non-nullable
    op.alter_column('boardgames', 'new_field', nullable=False)

def downgrade():
    op.drop_column('boardgames', 'new_field')
```

### 3. Test Migrations Locally First
```bash
# Test upgrade
alembic upgrade head

# Test downgrade
alembic downgrade -1

# Test re-upgrade
alembic upgrade head
```

### 4. Use Descriptive Migration Names
```bash
# Good
alembic revision --autogenerate -m "Add nz_designer index for performance"

# Bad
alembic revision --autogenerate -m "Update"
```

### 5. One Logical Change Per Migration
Don't combine unrelated changes in one migration for easier rollback.

## Deployment

### Development
```bash
# After pulling new code
alembic upgrade head
```

### Production (Render)
Add to your build/start commands in `render.yaml`:

```yaml
services:
  - type: web
    name: mana-meeples-api
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT"
```

### CI/CD
Add to GitHub Actions workflow:

```yaml
- name: Run migrations
  run: |
    cd backend
    alembic upgrade head
```

## Troubleshooting

### "Target database is not up to date"
```bash
# Check current revision
alembic current

# Check expected revision
alembic history

# If mismatch, either:
alembic stamp head  # Mark as current (dangerous, only if you know it's correct)
# OR
alembic upgrade head  # Apply missing migrations
```

### "Can't locate revision identified by 'head'"
```bash
# No migrations exist yet
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

### Migration Conflicts
```bash
# Multiple people created migrations simultaneously
# Alembic will create a merge migration
alembic merge heads -m "Merge migrations"
alembic upgrade head
```

## Migration Checklist

Before committing a migration:
- [ ] Reviewed generated migration code
- [ ] Added necessary data migrations
- [ ] Tested upgrade locally
- [ ] Tested downgrade locally
- [ ] Tested re-upgrade
- [ ] Added migration to version control
- [ ] Updated documentation if needed
- [ ] Verified no breaking changes for running systems

## Next Steps

1. **Install Alembic**: `pip install alembic==1.13.1`
2. **Initialize**: `alembic init alembic`
3. **Configure**: Edit `alembic.ini` and `alembic/env.py` as shown above
4. **Create baseline**: `alembic revision --autogenerate -m "Initial schema"`
5. **Remove in-code migrations**: Clean up `database.py`
6. **Update deployment**: Add `alembic upgrade head` to startup commands

## Resources

- [Alembic Official Documentation](https://alembic.sqlalchemy.org/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Autogenerate Documentation](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- [Migration Cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html)
