"""fix datetime timezone, boolean is_return, drop redundant index, add batches index

Revision ID: 6d0d1d058adc
Revises: 92c72a7b275e
Create Date: 2026-04-13 17:15:39.002178

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6d0d1d058adc'
down_revision: Union[str, None] = '92c72a7b275e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # DateTime timezone fixes
    op.alter_column('analysis_runs', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('products', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('products', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('upload_batches', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))

    # is_return: Integer → Boolean with server default
    op.alter_column('sales', 'is_return',
               existing_type=sa.INTEGER(),
               type_=sa.Boolean(),
               postgresql_using='is_return::boolean',
               nullable=False,
               server_default=sa.false())

    # Drop redundant index — PostgreSQL already indexes primary keys automatically
    op.drop_index('ix_products_product_id', table_name='products')

    # Add index on upload_batches.created_at — used for newest-first ordering
    op.create_index('ix_upload_batches_created_at', 'upload_batches', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_upload_batches_created_at', table_name='upload_batches')
    op.create_index('ix_products_product_id', 'products', ['product_id'], unique=False)

    op.alter_column('sales', 'is_return',
               existing_type=sa.Boolean(),
               type_=sa.INTEGER(),
               postgresql_using='is_return::integer',
               nullable=True,
               server_default=None)

    op.alter_column('upload_batches', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('products', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('products', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('analysis_runs', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True,
               existing_server_default=sa.text('now()'))

