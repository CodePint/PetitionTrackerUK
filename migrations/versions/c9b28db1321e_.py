"""empty message

Revision ID: c9b28db1321e
Revises: 44e4ef3e738c
Create Date: 2020-10-01 13:50:13.456780

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
from application.models import *
from application.tracker.models import *

import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = 'c9b28db1321e'
down_revision = '44e4ef3e738c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('task',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('interval', sqlalchemy_utils.types.json.JSONType(), nullable=True),
    sa.Column('last_run', sa.DateTime(), nullable=True),
    sa.Column('last_failed', sa.DateTime(), nullable=True),
    sa.Column('db_created_at', sa.DateTime(), nullable=True),
    sa.Column('db_updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('task_run',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('state', sqlalchemy_utils.types.choice.ChoiceType([(0, 'PENDING'), (1, 'RUNNING'), (2, 'COMPLETED'), (3, 'FAILED'), (4, 'REJECTED'), (5, 'RETRYING')]), nullable=False),
    sa.Column('args', sa.String(), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.Column('execution_time', sa.Integer(), nullable=True),
    sa.Column('db_created_at', sa.DateTime(), nullable=True),
    sa.Column('db_updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['task_id'], ['task.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_run_task_id'), 'task_run', ['task_id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_task_run_task_id'), table_name='task_run')
    op.drop_table('task_run')
    op.drop_table('task')
    # ### end Alembic commands ###
