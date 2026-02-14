from alembic import op
import sqlalchemy as sa

revision = "0003_fix_admin_users_columns"
down_revision = "0002_seed_admin"
branch_labels = None
depends_on = None

def upgrade():
    # 1) fullname (requerido por login)
    op.add_column("admin_users", sa.Column("fullname", sa.String(120), nullable=True))
    # 2) role (requerido por login)
    op.add_column("admin_users", sa.Column("role", sa.String(20), nullable=False, server_default="user"))
    # 3) is_active (si no existe o si tu tabla vieja no lo tenía)
    #    Si ya existe, esto fallará, entonces solo actívalo si confirmas que no está.
    # op.add_column("admin_users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    # Índices/unique como en tu modelo
    op.create_index("ix_admin_users_fullname", "admin_users", ["fullname"])
    op.create_unique_constraint("uq_admin_users_fullname", "admin_users", ["fullname"])

    # Backfill: para filas viejas que no tengan fullname
    op.execute("UPDATE admin_users SET fullname = username WHERE fullname IS NULL OR fullname = ''")

def downgrade():
    op.drop_constraint("uq_admin_users_fullname", "admin_users", type_="unique")
    op.drop_index("ix_admin_users_fullname", table_name="admin_users")
    op.drop_column("admin_users", "role")
    op.drop_column("admin_users", "fullname")
