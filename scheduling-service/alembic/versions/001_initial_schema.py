from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'skills',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_skills_id', 'skills', ['id'])
    op.create_index('ix_skills_name', 'skills', ['name'])

    op.create_table(
        'staff',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(200), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('max_hours_per_week', sa.Float(), nullable=False, server_default='40.0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_staff_id', 'staff', ['id'])
    op.create_index('ix_staff_email', 'staff', ['email'])

    op.create_table(
        'staff_skills',
        sa.Column('staff_id', sa.Integer(), nullable=False),
        sa.Column('skill_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['staff_id'], ['staff.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('staff_id', 'skill_id'),
    )

    op.create_table(
        'shifts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('location', sa.String(200), nullable=True),
        sa.Column('required_staff_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(50), nullable=False, server_default='unscheduled'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_shifts_id', 'shifts', ['id'])
    op.create_index('ix_shifts_date', 'shifts', ['date'])

    op.create_table(
        'shift_skill_requirements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shift_id', sa.Integer(), nullable=False),
        sa.Column('skill_id', sa.Integer(), nullable=False),
        sa.Column('required_count', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('shift_id', 'skill_id', name='uq_shift_skill'),
    )
    op.create_index('ix_shift_skill_requirements_id', 'shift_skill_requirements', ['id'])

    op.create_table(
        'shift_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shift_id', sa.Integer(), nullable=False),
        sa.Column('staff_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['staff_id'], ['staff.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('shift_id', 'staff_id', name='uq_shift_assignment'),
    )
    op.create_index('ix_shift_assignments_id', 'shift_assignments', ['id'])


def downgrade() -> None:
    op.drop_table('shift_assignments')
    op.drop_table('shift_skill_requirements')
    op.drop_table('shifts')
    op.drop_table('staff_skills')
    op.drop_table('staff')
    op.drop_table('skills')
