"""empty message

Revision ID: dee0ef42f3ca
Revises: 4a10fe959a7f
Create Date: 2020-09-15 18:14:33.284951

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
from application.models import *
from application.tracker.models import *



# revision identifiers, used by Alembic.
revision = 'dee0ef42f3ca'
down_revision = '4a10fe959a7f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('petition', sa.Column('pt_closed_at', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('petition', 'pt_closed_at')
    # ### end Alembic commands ###
