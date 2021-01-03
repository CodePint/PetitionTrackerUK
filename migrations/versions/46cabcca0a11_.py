"""empty message

Revision ID: 46cabcca0a11
Revises: 7812245fd360
Create Date: 2020-12-13 14:24:35.928860

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
from application.models import *
from application.tracker.models import *



# revision identifiers, used by Alembic.
revision = '46cabcca0a11'
down_revision = '7812245fd360'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('petition', 'action',
               existing_type=sa.VARCHAR(length=512),
               nullable=False)
    op.alter_column('petition', 'signatures',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_index('ix_petition_action', table_name='petition')
    op.create_index(op.f('ix_petition_action'), 'petition', ['action'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_petition_action'), table_name='petition')
    op.create_index('ix_petition_action', 'petition', ['action'], unique=True)
    op.alter_column('petition', 'signatures',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('petition', 'action',
               existing_type=sa.VARCHAR(length=512),
               nullable=True)
    # ### end Alembic commands ###
