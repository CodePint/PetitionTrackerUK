"""empty message

Revision ID: 722cb98d4464
Revises: 5a3739cf02bc
Create Date: 2020-11-10 18:27:56.465316

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
from application.models import *
from application.tracker.models import *

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '722cb98d4464'
down_revision = '5a3739cf02bc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('event',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('msg', sa.String(), nullable=True),
    sa.Column('ts', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_name'), 'event', ['name'], unique=False)
    op.create_index(op.f('ix_event_ts'), 'event', ['ts'], unique=False)
    op.add_column('petition', sa.Column('growth_rate', sa.Float(), nullable=True))
    op.add_column('petition', sa.Column('trend_position', sa.Integer(), nullable=True))
    op.drop_column('petition', 'trend_pos')
    op.drop_column('petition', 'geo_polled_at')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('petition', sa.Column('geo_polled_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('petition', sa.Column('trend_pos', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_column('petition', 'trend_position')
    op.drop_column('petition', 'growth_rate')
    op.drop_index(op.f('ix_event_ts'), table_name='event')
    op.drop_index(op.f('ix_event_name'), table_name='event')
    op.drop_table('event')
    # ### end Alembic commands ###
