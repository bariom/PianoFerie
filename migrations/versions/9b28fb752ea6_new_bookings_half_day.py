"""New bookings half day

Revision ID: 9b28fb752ea6
Revises: 3d90ffb9ba80
Create Date: 2024-12-02 15:57:45.703700

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b28fb752ea6'
down_revision = '3d90ffb9ba80'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('booking', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_half_day', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('session', sa.String(length=10), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('booking', schema=None) as batch_op:
        batch_op.drop_column('session')
        batch_op.drop_column('is_half_day')

    # ### end Alembic commands ###
