import time
import os
from decimal import Decimal, InvalidOperation
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from .auth import CurrentUser, DB, require_origin
from .marketplaces import PROVIDERS
from .models import AuditEvent, CatalogProduct, ChatTurn, CollectionItem, PriceSnapshot, User

router = APIRouter(prefix="/api/auth", dependencies=[Depends(require_origin)])
Kind = Literal["wishlist", "saved", "recent", "compare"]
KINDS = ("wishlist", "saved", "recent", "compare")


class CollectionAction(BaseModel):
    kind: Kind
    product_id: int = Field(gt=0)
    selected: bool


class DemoProductEdit(BaseModel):
    id: int = Field(gt=0)
    price_inr: int = Field(ge=0, le=10000000)
    description: str = Field(min_length=1, max_length=1200, pattern=r"\S")


def collection_ids(db, user):
    result = {kind: [] for kind in KINDS}
    rows = db.scalars(select(CollectionItem).where(CollectionItem.user_id == user.id)
                      .order_by(CollectionItem.updated_at.desc(), CollectionItem.product_id))
    for row in rows:
        result[row.kind].append(row.product_id)
    return result


@router.get("/collections")
def collections(db: DB, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return collection_ids(db, user)


@router.patch("/collections")
def update_collections(action: CollectionAction, db: DB, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    db.execute(select(User.id).where(User.id == user.id).with_for_update())
    key = (user.id, action.kind, action.product_id)
    item = db.get(CollectionItem, key)
    if action.selected:
        if db.get(CatalogProduct, action.product_id) is None:
            raise HTTPException(404, "Product not found")
        if item is None:
            item = CollectionItem(user_id=user.id, kind=action.kind, product_id=action.product_id, updated_at=0)
            db.add(item)
        item.updated_at = time.time_ns()
        db.flush()
        limit = {"compare": 4, "recent": 12}.get(action.kind)
        if limit:
            rows = list(db.scalars(select(CollectionItem).where(
                CollectionItem.user_id == user.id, CollectionItem.kind == action.kind,
            ).order_by(CollectionItem.updated_at.desc(), CollectionItem.product_id).offset(limit)))
            if action.kind == "compare" and rows:
                raise HTTPException(409, "Compare up to four products")
            for old in rows:
                db.delete(old)
    elif item is not None:
        db.delete(item)
    result = collection_ids(db, user)
    db.commit()
    return result


@router.get("/admin")
def admin_statistics(db: DB, user: CurrentUser, response: Response):
    if user.role != "admin":
        raise HTTPException(403, "Administrator access is required")
    response.headers["Cache-Control"] = "no-store"
    result = {
        "users": db.scalar(select(func.count()).select_from(User)),
        "verified_users": db.scalar(select(func.count()).select_from(User).where(User.verified.is_(True))),
        "catalog_products": db.scalar(select(func.count()).select_from(CatalogProduct)),
        "collection_items": db.scalar(select(func.count()).select_from(CollectionItem)),
        "chat_turns": db.scalar(select(func.count()).select_from(ChatTurn)),
        "input_tokens": db.scalar(select(func.coalesce(func.sum(ChatTurn.input_tokens), 0))),
        "output_tokens": db.scalar(select(func.coalesce(func.sum(ChatTurn.output_tokens), 0))),
        "price_snapshots": db.scalar(select(func.count()).select_from(PriceSnapshot)),
        "catalog_audit_events": db.scalar(select(func.count()).select_from(AuditEvent)),
        "amazon": "Configured" if PROVIDERS["amazon"].configured() else "Awaiting credentials",
        "flipkart": "Configured" if PROVIDERS["flipkart"].configured() else "Awaiting credentials",
        "database": "Connected",
    }
    model = os.getenv("OPENAI_MODEL")
    if model:
        try:
            input_rate = Decimal(os.getenv("OPENAI_ESTIMATE_INPUT_USD_PER_MILLION") or "")
            output_rate = Decimal(os.getenv("OPENAI_ESTIMATE_OUTPUT_USD_PER_MILLION") or "")
            if all(rate.is_finite() and 0 <= rate <= 10**6 for rate in (input_rate, output_rate)):
                input_total, output_total = db.execute(select(
                    func.coalesce(func.sum(ChatTurn.input_tokens), 0),
                    func.coalesce(func.sum(ChatTurn.output_tokens), 0),
                ).where(ChatTurn.model == model)).one()
                result["estimated_cost"] = f"${(input_total * input_rate + output_total * output_rate) / 10**6:.6f} ({model})"
        except InvalidOperation:
            pass
    return result


@router.patch("/admin")
def update_demo_product(payload: DemoProductEdit, db: DB, user: CurrentUser, response: Response):
    if user.role != "admin":
        raise HTTPException(403, "Administrator access is required")
    response.headers["Cache-Control"] = "no-store"
    product = db.scalar(select(CatalogProduct).where(CatalogProduct.id == payload.id).with_for_update())
    if product is None or product.data_status != "sample":
        raise HTTPException(404, "Demo product not found")
    description = payload.description.strip()
    now = int(time.time())
    if product.price_inr != payload.price_inr:
        db.add(PriceSnapshot(product_id=product.id, price_inr=payload.price_inr, recorded_at=now))
    if product.price_inr != payload.price_inr or product.description != description:
        db.add(AuditEvent(actor_id=user.id, action="catalog.demo.update", target=str(product.id), recorded_at=now))
        product.price_inr = payload.price_inr
        product.description = description
    db.commit()
    return {"updated": product.id}
