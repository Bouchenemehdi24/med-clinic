from alembic import op
import sqlalchemy as sa

def upgrade():
    # Ajout des colonnes pour la première consultation
    op.add_column('patient', sa.Column('first_consultation_diagnostic', sa.Text))
    op.add_column('patient', sa.Column('first_consultation_treatment', sa.Text))
    op.add_column('patient', sa.Column('first_consultation_notes', sa.Text))
    op.add_column('patient', sa.Column('risk_category', sa.String(20), nullable=False, server_default='normal'))

def downgrade():
    op.drop_column('patient', 'first_consultation_diagnostic')
    op.drop_column('patient', 'first_consultation_treatment')
    op.drop_column('patient', 'first_consultation_notes')
    op.drop_column('patient', 'risk_category')
