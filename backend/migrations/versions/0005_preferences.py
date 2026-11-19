from alembic import op
import sqlalchemy as sa

revision = "0005_preferences"
down_revision = "0004_chat"


def upgrade():
    op.create_table(
        "shopping_profiles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("budget_inr", sa.Integer()),
        sa.Column("keep_search_history", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "search_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query", sa.String(120), nullable=False),
    )
    op.create_index("ix_search_events_user_id", "search_events", ["user_id"])


def downgrade():
    op.drop_table("search_events")
    op.drop_table("shopping_profiles")
