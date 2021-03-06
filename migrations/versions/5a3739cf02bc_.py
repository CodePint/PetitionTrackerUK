"""empty message

Revision ID: 5a3739cf02bc
Revises: bf7ada70e567
Create Date: 2020-10-29 19:30:31.870993

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
from application.models import *
from application.tracker.models import *

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5a3739cf02bc'
down_revision = 'bf7ada70e567'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('task', sa.Column('description', sa.String(), nullable=True))
    op.add_column('task', sa.Column('key', sa.String(), nullable=False))
    op.add_column('task', sa.Column('kwargs', sqlalchemy_utils.types.json.JSONType(), nullable=True))
    op.add_column('task', sa.Column('last_success', sa.DateTime(), nullable=True))
    op.add_column('task', sa.Column('module', sa.String(), nullable=False))
    op.add_column('task', sa.Column('opts', sqlalchemy_utils.types.json.JSONType(), nullable=True))
    op.add_column('task', sa.Column('periodic', sa.Boolean(), nullable=True))
    op.add_column('task', sa.Column('schedule', sqlalchemy_utils.types.json.JSONType(), nullable=True))
    op.add_column('task', sa.Column('startup', sa.Boolean(), nullable=True))
    op.create_unique_constraint('uniq_name_key_for_task', 'task', ['name', 'key'])
    op.drop_constraint('task_name_key', 'task', type_='unique')
    op.drop_column('task', 'interval')
    op.drop_column('task', 'last_run')
    op.drop_column('task', 'run_on_startup')
    op.add_column('task_run', sa.Column('error', sa.String(), nullable=True))
    op.add_column('task_run', sa.Column('kwargs', sqlalchemy_utils.types.json.JSONType(), nullable=True))
    op.add_column('task_run', sa.Column('lock_key', sa.String(), nullable=True))
    op.add_column('task_run', sa.Column('max_retries', sa.Integer(), nullable=True))
    op.add_column('task_run', sa.Column('result', sqlalchemy_utils.types.json.JSONType(), nullable=True))
    op.add_column('task_run', sa.Column('retries_countdown', sa.Integer(), nullable=True))
    op.add_column('task_run', sa.Column('revoke_msg', sa.String(), nullable=True))
    op.add_column('task_run', sa.Column('unique', sa.Boolean(), nullable=True))
    op.alter_column('task_run', 'celery_id',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.drop_column('task_run', 'args')
    op.drop_column('task_run', 'execution_time')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('task_run', sa.Column('execution_time', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('task_run', sa.Column('args', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.alter_column('task_run', 'celery_id',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_column('task_run', 'unique')
    op.drop_column('task_run', 'revoke_msg')
    op.drop_column('task_run', 'retries_countdown')
    op.drop_column('task_run', 'result')
    op.drop_column('task_run', 'max_retries')
    op.drop_column('task_run', 'lock_key')
    op.drop_column('task_run', 'kwargs')
    op.drop_column('task_run', 'error')
    op.add_column('task', sa.Column('run_on_startup', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('task', sa.Column('last_run', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('task', sa.Column('interval', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True))
    op.create_unique_constraint('task_name_key', 'task', ['name'])
    op.drop_constraint('uniq_name_key_for_task', 'task', type_='unique')
    op.drop_column('task', 'startup')
    op.drop_column('task', 'schedule')
    op.drop_column('task', 'periodic')
    op.drop_column('task', 'opts')
    op.drop_column('task', 'module')
    op.drop_column('task', 'last_success')
    op.drop_column('task', 'kwargs')
    op.drop_column('task', 'key')
    op.drop_column('task', 'description')
    # ### end Alembic commands ###
