"""empty message

Revision ID: 5c2c48355ad6
Revises: 324c2b281378
Create Date: 2020-10-02 16:57:39.467643

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
from application.models import *
from application.tracker.models import *



# revision identifiers, used by Alembic.
revision = '5c2c48355ad6'
down_revision = '324c2b281378'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('record', sa.Column('geographic', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('record', 'geographic')
    # ### end Alembic commands ###
