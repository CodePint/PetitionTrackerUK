"""empty message

Revision ID: d5854e3c412e
Revises: 
Create Date: 2020-06-29 16:35:16.927193

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
from PetitionTracker.tracker.models import *

import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = 'd5854e3c412e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('petition',
    sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('state', sqlalchemy_utils.types.choice.ChoiceType([('C', 'closed'), ('R', 'rejected'), ('O', 'open')]), nullable=False),
    sa.Column('action', sa.String(length=512), nullable=True),
    sa.Column('signatures', sa.Integer(), nullable=True),
    sa.Column('url', sa.String(length=2048), nullable=True),
    sa.Column('background', sa.String(), nullable=True),
    sa.Column('additional_details', sa.String(), nullable=True),
    sa.Column('pt_created_at', sa.DateTime(), nullable=True),
    sa.Column('pt_updated_at', sa.DateTime(), nullable=True),
    sa.Column('pt_rejected_at', sa.DateTime(), nullable=True),
    sa.Column('db_created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('db_updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('initial_data', sqlalchemy_utils.types.json.JSONType(), nullable=True),
    sa.Column('latest_data', sqlalchemy_utils.types.json.JSONType(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_petition_action'), 'petition', ['action'], unique=True)
    op.create_index(op.f('ix_petition_url'), 'petition', ['url'], unique=True)
    op.create_table('record',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('petition_id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
    sa.Column('signatures', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['petition_id'], ['petition.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('signatures_by_constituency',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('record_id', sa.Integer(), nullable=True),
    sa.Column('ons_code', sa.String(length=9), nullable=True),
    sa.Column('count', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['record_id'], ['record.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('record_id', 'ons_code', name='uniq_sig_constituency_for_record')
    )
    op.create_table('signatures_by_country',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('record_id', sa.Integer(), nullable=True),
    sa.Column('iso_code', sa.String(length=3), nullable=True),
    sa.Column('count', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['record_id'], ['record.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('record_id', 'iso_code', name='uniq_sig_country_for_record')
    )
    op.create_table('signatures_by_region',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('record_id', sa.Integer(), nullable=True),
    sa.Column('ons_code', sa.String(length=3), nullable=True),
    sa.Column('count', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['record_id'], ['record.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('record_id', 'ons_code', name='uniq_sig_region_for_record')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('signatures_by_region')
    op.drop_table('signatures_by_country')
    op.drop_table('signatures_by_constituency')
    op.drop_table('record')
    op.drop_index(op.f('ix_petition_url'), table_name='petition')
    op.drop_index(op.f('ix_petition_action'), table_name='petition')
    op.drop_table('petition')
    # ### end Alembic commands ###