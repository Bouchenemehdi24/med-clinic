from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('app_settings',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('app_name', sa.String(100), nullable=False, server_default='Clinique Médicale'),
        sa.Column('logo_url', sa.String(200)),
        sa.Column('primary_color', sa.String(20), server_default='#0d6efd'),
        sa.Column('last_updated', sa.DateTime, server_default=sa.func.now())
    )

def downgrade():
    op.drop_table('app_settings')
