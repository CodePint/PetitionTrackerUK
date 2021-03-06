"""empty message

Revision ID: b9619b132046
Revises: 77ff383eaf62
Create Date: 2020-07-15 14:57:59.063877

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
from application.models import *
from application.tracker.models import *



# revision identifiers, used by Alembic.
revision = 'b9619b132046'
down_revision = '77ff383eaf62'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('setting',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(), nullable=True),
    sa.Column('value', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_setting_key'), 'setting', ['key'], unique=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_setting_key'), table_name='setting')
    op.drop_table('setting')
    # ### end Alembic commands ###
