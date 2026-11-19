from alembic import op
import sqlalchemy as sa

revision = "0003_collections"
down_revision = "0002_catalog"


def upgrade():
    op.create_table(
        "collection_items",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("kind", sa.String(12), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("catalog_products.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )


def downgrade():
    op.drop_table("collection_items")
