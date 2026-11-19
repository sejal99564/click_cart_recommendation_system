from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(180))
    name: Mapped[str] = mapped_column(String(100))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[str] = mapped_column(String(24), default="customer")


class Credential(Base):
    __tablename__ = "credentials"

    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(16))
    expires_at: Mapped[int] = mapped_column(BigInteger, index=True)

class CatalogProduct(Base):
    __tablename__ = "catalog_products"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80), index=True)
    price_inr: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(1200))
    data_status: Mapped[str] = mapped_column(String(20), default="sample")
    source_url: Mapped[str | None] = mapped_column(String(2048))
    marketplace: Mapped[str] = mapped_column(String(60), default="Demo catalog")
    specifications: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)


class CollectionItem(Base):
    __tablename__ = "collection_items"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[str] = mapped_column(String(12), primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("catalog_products.id", ondelete="CASCADE"), primary_key=True)
    updated_at: Mapped[int] = mapped_column(BigInteger)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[int] = mapped_column(BigInteger)


class ChatTurn(Base):
    __tablename__ = "chat_turns"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    question: Mapped[str] = mapped_column(String(2000))
    answer: Mapped[str] = mapped_column(Text)
    products: Mapped[list[dict]] = mapped_column(JSON)
    model: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)


class ShoppingProfile(Base):
    __tablename__ = "shopping_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    budget_inr: Mapped[int | None] = mapped_column(Integer)
    keep_search_history: Mapped[bool] = mapped_column(Boolean, default=False)


class SearchEvent(Base):
    __tablename__ = "search_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    query: Mapped[str] = mapped_column(String(120))

class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("catalog_products.id", ondelete="CASCADE"), index=True)
    price_inr: Mapped[int] = mapped_column(Integer)
    recorded_at: Mapped[int] = mapped_column(BigInteger)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(70))
    target: Mapped[str] = mapped_column(String(80))
    recorded_at: Mapped[int] = mapped_column(BigInteger)
