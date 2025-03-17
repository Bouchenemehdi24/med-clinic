try:
    from alembic import op
    import sqlalchemy as sa
except ImportError:
    print("Alembic n'est pas installé. Exécutez 'pip install alembic'")

def upgrade():
    op.add_column('app_settings', sa.Column('clinic_address', sa.Text))

def downgrade():
    op.drop_column('app_settings', 'clinic_address')
