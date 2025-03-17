from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('app_settings', sa.Column('header_image', sa.LargeBinary))
    op.add_column('app_settings', sa.Column('header_image_type', sa.String(32)))
    op.add_column('app_settings', sa.Column('footer_text', sa.Text))
    op.add_column('app_settings', sa.Column('stamp_image', sa.LargeBinary))
    op.add_column('app_settings', sa.Column('stamp_image_type', sa.String(32)))

def downgrade():
    op.drop_column('app_settings', 'header_image')
    op.drop_column('app_settings', 'header_image_type')
    op.drop_column('app_settings', 'footer_text')
    op.drop_column('app_settings', 'stamp_image')
    op.drop_column('app_settings', 'stamp_image_type')
