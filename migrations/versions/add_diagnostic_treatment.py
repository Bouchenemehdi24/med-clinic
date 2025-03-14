from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('patient', sa.Column('diagnostic', sa.Text))
    op.add_column('patient', sa.Column('treatment', sa.Text))

def downgrade():
    op.drop_column('patient', 'diagnostic')
    op.drop_column('patient', 'treatment')
