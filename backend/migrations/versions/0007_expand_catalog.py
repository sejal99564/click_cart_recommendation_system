"""Add illustrative choices for headphone, laptop and smartphone searches."""
import json

from alembic import op
import sqlalchemy as sa

revision = "0007_expand_catalog"
down_revision = "0006_catalog_audit"


ITEMS = (
    (5, "Sample Wireless Travel Headphones", "Audio", 5499, "Foldable wireless headphones for travel, with active noise cancellation.", {"Connectivity": "Bluetooth", "Noise cancellation": "Active", "Battery": "30 hours"}),
    (6, "Sample Wireless Sport Headphones", "Audio", 3499, "Lightweight wireless headphones for exercise and daily listening.", {"Connectivity": "Bluetooth", "Water resistance": "IPX4", "Battery": "18 hours"}),
    (7, "Sample Portable Work Laptop", "Laptops", 59999, "A lightweight laptop for office work, study, and video calls.", {"Memory": "16 GB", "Storage": "512 GB SSD", "Weight": "1.35 kg"}),
    (8, "Sample Entry-Level Study Laptop", "Laptops", 39999, "An affordable laptop for web browsing, documents, and remote classes.", {"Memory": "8 GB", "Storage": "256 GB SSD", "Weight": "1.55 kg"}),
    (9, "Sample Everyday 5G Smartphone", "Phones", 24999, "A midrange smartphone for everyday apps and photos, with a large battery.", {"Network": "5G", "Battery": "5,000 mAh", "Storage": "128 GB"}),
    (10, "Sample Budget 5G Smartphone", "Phones", 15999, "A lower-priced smartphone for calls, messaging, and basic apps.", {"Network": "5G", "Battery": "5,000 mAh", "Storage": "128 GB"}),
)


def upgrade():
    for product_id, title, category, price, description, specs in ITEMS:
        statement = sa.text("""
            INSERT INTO catalog_products
                (id, title, category, price_inr, description, data_status, marketplace, specifications)
            VALUES (:id, :title, :category, :price, :description, 'sample', 'Demo catalog', CAST(:specs AS JSON))
        """ if op.get_context().dialect.name == "postgresql" else """
            INSERT INTO catalog_products
                (id, title, category, price_inr, description, data_status, marketplace, specifications)
            VALUES (:id, :title, :category, :price, :description, 'sample', 'Demo catalog', :specs)
        """)
        values = {"id": product_id, "title": title, "category": category, "price": price, "description": description, "specs": json.dumps(specs)}
        params = [sa.bindparam(key, op.inline_literal(value).value) for key, value in values.items()] if op.get_context().as_sql else []
        if params:
            op.execute(statement.bindparams(*params))
        else:
            op.get_bind().execute(statement, values)


def downgrade():
    op.execute("DELETE FROM catalog_products WHERE id BETWEEN 5 AND 10 AND data_status = 'sample'")
