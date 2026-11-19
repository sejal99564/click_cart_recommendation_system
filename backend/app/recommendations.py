from fastapi import APIRouter, Response
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import aliased

from .auth import CurrentUser, DB
from .catalog import Product
from .models import CatalogProduct, CollectionItem, ShoppingProfile

router = APIRouter(prefix="/api/auth")


@router.get("/recommendations", response_model=list[Product])
def recommend(db: DB, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    saved = db.get(ShoppingProfile, user.id)
    preference = set(saved.categories) if saved else set()
    own = db.execute(select(CollectionItem.product_id, CatalogProduct.category)
                     .join(CatalogProduct, CollectionItem.product_id == CatalogProduct.id)
                     .where(CollectionItem.user_id == user.id, CollectionItem.kind.in_(("wishlist", "saved", "recent"))))
    known = {product_id: category for product_id, category in own}
    categories = set(known.values()) | preference
    candidates = select(CatalogProduct).order_by(CatalogProduct.id).limit(100)
    if known:
        candidates = candidates.where(CatalogProduct.id.not_in(known))
    if saved and saved.budget_inr is not None:
        candidates = candidates.where(CatalogProduct.price_inr <= saved.budget_inr)
    products = list(db.scalars(candidates))

    behavior = aliased(CollectionItem)
    signals = ("wishlist", "saved")
    signal = func.count(distinct(behavior.user_id))
    aggregate = select(behavior.product_id, signal).where(
        behavior.kind.in_(signals), behavior.user_id != user.id,
        behavior.product_id.in_([product.id for product in products]),
    )
    if known:
        neighbors = select(CollectionItem.user_id).where(CollectionItem.product_id.in_(known), CollectionItem.kind.in_(signals))
        aggregate = aggregate.where(behavior.user_id.in_(neighbors))
    popularity = dict(db.execute(aggregate.group_by(behavior.product_id).having(signal >= 3)).all())
    max_signal = max(popularity.values(), default=1)

    def score(product):
        content = 1.0 if product.category in preference else 0.8 if product.category in categories else 0.0
        return 0.65 * content + 0.35 * popularity.get(product.id, 0) / max_signal

    ranked = sorted(products, key=lambda product: (-score(product), product.id))
    return [product for product in ranked[:8] if score(product) > 0]
