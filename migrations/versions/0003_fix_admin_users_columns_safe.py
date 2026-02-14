from alembic import op

# Ponle un id real (puede ser random estilo alembic)
revision = "0003_fix_admin_users_columns_safe"
down_revision = "ab5c175ea638"  # <-- ajusta al último revision real en tu repo
branch_labels = None
depends_on = None


def upgrade():
    # 1) Columnas (safe)
    op.execute("""
        ALTER TABLE admin_users
        ADD COLUMN IF NOT EXISTS fullname VARCHAR(120);
    """)

    op.execute("""
        ALTER TABLE admin_users
        ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user';
    """)

    # 2) Backfill (para registros existentes)
    op.execute("""
        UPDATE admin_users
        SET fullname = COALESCE(NULLIF(fullname, ''), username)
        WHERE fullname IS NULL OR fullname = '';
    """)

    # 3) Índices/constraints (safe-ish)
    # Índice
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'ix_admin_users_fullname'
            ) THEN
                CREATE INDEX ix_admin_users_fullname ON admin_users (fullname);
            END IF;
        END$$;
    """)

    # Unique constraint
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_admin_users_fullname'
            ) THEN
                ALTER TABLE admin_users
                ADD CONSTRAINT uq_admin_users_fullname UNIQUE (fullname);
            END IF;
        END$$;
    """)


def downgrade():
    # Ojo: en BD viva normalmente no conviene bajar, pero lo dejamos razonable.
    op.execute("ALTER TABLE admin_users DROP CONSTRAINT IF EXISTS uq_admin_users_fullname;")
    op.execute("DROP INDEX IF EXISTS ix_admin_users_fullname;")
    op.execute("ALTER TABLE admin_users DROP COLUMN IF EXISTS role;")
    op.execute("ALTER TABLE admin_users DROP COLUMN IF EXISTS fullname;")
