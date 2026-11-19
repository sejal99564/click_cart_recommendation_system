from alembic import op
import sqlalchemy as sa

revision = "0001_identity"
down_revision = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(180), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("role", sa.String(24), nullable=False),
    )
    op.create_table(
        "credentials",
        sa.Column("digest", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_credentials_user_id", "credentials", ["user_id"])
    op.create_index("ix_credentials_expires_at", "credentials", ["expires_at"])


def downgrade():
    op.drop_table("credentials")
    op.drop_table("users")
