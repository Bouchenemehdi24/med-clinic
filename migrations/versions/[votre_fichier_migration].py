"""add weight column to patient

Revision ID: [votre_id]
Revises: [revision_precedente]
Create Date: [date]
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError

def upgrade():
    try:
        with op.batch_alter_table('patient') as batch_op:
            batch_op.add_column(sa.Column('weight', sa.Float, nullable=True))
    except OperationalError as e:
        if 'duplicate column name' not in str(e):
            raise e

def downgrade():
    try:
        with op.batch_alter_table('patient') as batch_op:
            batch_op.drop_column('weight')
    except OperationalError as e:
        if 'no such column' not in str(e):
            raise e
