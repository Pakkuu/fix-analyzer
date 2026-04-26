"""
Alembic env.py — auto-generated, then customised for fix-analyzer.

Configured for manual migrations since we are not using an ORM.
"""

from logging.config import fileConfig

from sqlalchemy import pool
from alembic import context

# ── project imports ─────────────────────────────────────────────────────
from database.connection import engine, DATABASE_URL

# ── Alembic config object ──────────────────────────────────────────────
config = context.config

# Override the ini-file URL with the one from connection.py
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Python logging from the config file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No ORM models, so no autogenerate metadata
target_metadata = None


# ── offline mode ────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a live DB)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── online mode ─────────────────────────────────────────────────────────

def run_migrations_online() -> None:
    """Run migrations in 'online' mode (using the shared engine)."""
    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
