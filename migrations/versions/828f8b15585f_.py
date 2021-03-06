"""empty message

Revision ID: 828f8b15585f
Revises: d7cdfd83d07b
Create Date: 2020-08-23 16:02:30.058592

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
from application.models import *
from application.tracker.models import *



# revision identifiers, used by Alembic.
revision = '828f8b15585f'
down_revision = 'd7cdfd83d07b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('petition', sa.Column('polled_at', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('petition', 'polled_at')
    # ### end Alembic commands ###
