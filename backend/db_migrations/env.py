from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
import os

# 1) citește URL din app.config (din .env), ca să nu-l duplici în alembic.ini
from app.config import settings

config = context.config
fileConfig(config.config_file_name)

# sincronizează URL-ul în config (offline/online)
config.set_main_option("sqlalchemy.url", settings.database_url)

# Pentru autogenerate, vom seta metadata mai târziu (când adăugăm modele).
target_metadata = None

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
