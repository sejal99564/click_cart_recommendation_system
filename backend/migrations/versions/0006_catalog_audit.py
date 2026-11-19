from alembic import op
import sqlalchemy as sa

revision = "0006_catalog_audit"
down_revision = "0005_preferences"


def upgrade():
    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("catalog_products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price_inr", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("price_inr >= 0", name="ck_snapshot_price"),
    )
    op.create_index("ix_price_snapshots_product_id", "price_snapshots", ["product_id"])
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(70), nullable=False),
        sa.Column("target", sa.String(80), nullable=False),
        sa.Column("recorded_at", sa.BigInteger(), nullable=False),
    )


def downgrade():
    op.drop_table("audit_events")
    op.drop_table("price_snapshots")
