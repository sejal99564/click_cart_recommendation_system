from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import DB
from .models import CatalogProduct, PriceSnapshot

router = APIRouter(prefix="/api/products")


class Product(BaseModel):
    id: int
    title: str
    category: str
    price_inr: int
    description: str
    data_status: str = "sample"
    source_url: str | None = None
    marketplace: str = "Demo catalog"
    specifications: dict[str, str] = Field(default_factory=dict)


def search_catalog(db: Session, query: str = "", budget: int | None = None, limit: int = 100, offset: int = 0, *, category: str | None = None):
    statement = select(CatalogProduct).order_by(CatalogProduct.id).limit(limit).offset(offset)
    if needle := query.strip().lower():
        text = func.lower(CatalogProduct.title + " " + CatalogProduct.category + " " + CatalogProduct.description)
        statement = statement.where(text.contains(needle, autoescape=True))
    if budget is not None:
        statement = statement.where(CatalogProduct.price_inr <= budget)
    if category is not None:
        statement = statement.where(CatalogProduct.category == category)
    return list(db.scalars(statement))


@router.get("", response_model=list[Product])
def products(db: DB, q: str = Query(default="", max_length=120), limit: int = Query(100, ge=1, le=100), offset: int = Query(0, ge=0)):
    return search_catalog(db, q, limit=limit, offset=offset)


@router.get("/{product_id}", response_model=Product)
def product(product_id: int, db: DB):
    item = db.get(CatalogProduct, product_id)
    if item is None:
        raise HTTPException(404, "Product not found")
    return item


@router.get("/{product_id}/prices")
def price_history(product_id: int, db: DB):
    item = product(product_id, db)
    rows = db.scalars(select(PriceSnapshot).where(PriceSnapshot.product_id == product_id)
                      .order_by(PriceSnapshot.id.desc()).limit(30))
    return {
        "data_status": item.data_status,
        "snapshots": [{"price_inr": row.price_inr, "recorded_at": row.recorded_at} for row in rows],
    }
