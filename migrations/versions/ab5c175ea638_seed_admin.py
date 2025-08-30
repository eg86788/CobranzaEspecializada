from alembic import op
import sqlalchemy as sa
from werkzeug.security import generate_password_hash

revision = '0002_seed_admin'
down_revision = '0001_base'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    conn.execute(
        sa.text("INSERT INTO admin_users (username, password_hash) VALUES (:u, :p)"),
        {"u":"admin", "p": generate_password_hash("admin123")}
    )

def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM admin_users WHERE username=:u"), {"u":"admin"})
