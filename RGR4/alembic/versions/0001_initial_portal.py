"""Create the incident coordination portal schema."""

from alembic import op

from app.database import Base
from app import models  # noqa: F401 - register all ORM tables


revision = "0001_initial_portal"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The ORM is the single source of truth for this first revision. This keeps
    # PostgreSQL enum definitions identical to the runtime models.
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
