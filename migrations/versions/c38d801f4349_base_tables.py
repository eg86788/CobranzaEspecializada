from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '0001_base'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # document_templates
    op.create_table(
        'document_templates',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('slug', sa.String(120), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('content_html', sa.Text, nullable=False),
        sa.Column('css', sa.Text, nullable=True),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('updated_by', sa.String(120), nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()'))
    )
    op.create_unique_constraint(
        "document_templates_slug_version_key",
        "document_templates", ["slug","version"]
    )

    # admin_users
    op.create_table(
        'admin_users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('username', sa.String(120), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()'))
    )

    # catálogo de números de adhesión
    op.create_table(
        'catalogo_adhesiones',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('clave', sa.String(100), nullable=False),   # ej: SEF_TRADICIONAL, SEF_ELECTRONICO
        sa.Column('numero', sa.String(100), nullable=False),  # número de adhesión
        sa.Column('vigente_desde', sa.Date, nullable=False),
        sa.Column('vigente_hasta', sa.Date, nullable=True),
        sa.Column('activo', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('updated_by', sa.String(120), nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()'))
    )
    op.create_index('idx_adhesiones_clave', 'catalogo_adhesiones', ['clave'])

def downgrade():
    op.drop_index('idx_adhesiones_clave', table_name='catalogo_adhesiones')
    op.drop_table('catalogo_adhesiones')
    op.drop_table('admin_users')
    op.drop_constraint("document_templates_slug_version_key", "document_templates", type_='unique')
    op.drop_table('document_templates')
