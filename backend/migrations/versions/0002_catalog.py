from alembic import op
import sqlalchemy as sa

revision = "0002_catalog"
down_revision = "0001_identity"


def upgrade():
    catalog = op.create_table(
        "catalog_products",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("price_inr", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(1200), nullable=False),
        sa.Column("data_status", sa.String(20), nullable=False),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("marketplace", sa.String(60), nullable=False),
        sa.Column("specifications", sa.JSON(), nullable=False),
        sa.CheckConstraint("price_inr >= 0", name="ck_catalog_price"),
    )
    op.create_index("ix_catalog_products_category", "catalog_products", ["category"])
    examples = [
        (1, "Sample Everyday Laptop", "Laptops", 49999, "Illustrative 16GB RAM laptop listing", {"Memory": "16 GB"}),
        (2, "Sample Camera Smartphone", "Phones", 24999, "Illustrative camera-focused phone listing", {}),
        (3, "Sample Wireless Headphones", "Audio", 2999, "Illustrative over-ear headphone listing", {"Form factor": "Over-ear", "Connectivity": "Wireless"}),
        (4, "Sample Gaming Laptop", "Laptops", 69999, "Illustrative discrete-GPU laptop listing", {"Graphics": "Discrete GPU"}),
    ]
    if op.get_context().as_sql:
        insert_catalog = sa.table(catalog.name, *(sa.column(column.name, sa.String() if column.name == "specifications" else column.type) for column in catalog.columns))
        import json
        examples = [(id_, title, category, price, description, json.dumps(specifications))
                    for id_, title, category, price, description, specifications in examples]
    else:
        insert_catalog = catalog
    op.bulk_insert(insert_catalog, [
        dict(id=id_, title=title, category=category, price_inr=price, description=description,
             data_status="sample", source_url=None, marketplace="Demo catalog", specifications=specifications)
        for id_, title, category, price, description, specifications in examples
    ])


def downgrade():
    op.drop_table("catalog_products")
