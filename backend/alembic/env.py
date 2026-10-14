from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import your models and database config
from models import Base
from config import DATABASE_URL, MIGRATION_LOCK_TIMEOUT_SECONDS
from utils.db_settings import install_session_settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the database URL from config
config.set_main_option('sqlalchemy.url', DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    # A migration that cannot get its table lock must FAIL (loudly) rather than wait
    # forever and hang the deploy. No idle-in-transaction cap: DDL can legitimately run long.
    install_session_settings(
        connectable,
        lock_timeout_s=MIGRATION_LOCK_TIMEOUT_SECONDS,
        idle_in_tx_timeout_s=0,
        application_name="alembic-migration",
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # Detect column type changes
            compare_server_default=True,  # Detect default value changes
            transaction_per_migration=True,  # Release table locks between migrations
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
