"""empty message

Revision ID: 718fa0099b10
Revises: 9c2154fff738
Create Date: 2020-10-12 19:03:56.471045

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
from application.models import *
from application.tracker.models import *



# revision identifiers, used by Alembic.
revision = '718fa0099b10'
down_revision = '9c2154fff738'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('task', 'enabled',
        existing_type=sa.BOOLEAN(),
        nullable=True
    )
    op.alter_column('task', 'run_on_startup',
        existing_type=sa.BOOLEAN(),
        nullable=True
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('task', 'run_on_startup',
        existing_type=sa.BOOLEAN(),
        nullable=False
    )
    op.alter_column('task', 'enabled',
        existing_type=sa.BOOLEAN(),
        nullable=False
    )
    # ### end Alembic commands ###