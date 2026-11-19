from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from .auth import CurrentUser, DB, require_origin
from .models import SearchEvent, ShoppingProfile, User

router = APIRouter(prefix="/api/auth", dependencies=[Depends(require_origin)])


class Preferences(BaseModel):
    categories: list[Literal["Laptops", "Phones", "Audio"]] = Field(default_factory=list, max_length=3)
    budget_inr: int | None = Field(None, ge=0, le=10000000)
    keep_search_history: bool = False


class SearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=120, pattern=r"\S")


@router.get("/preferences", response_model=Preferences)
def read_preferences(db: DB, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return db.get(ShoppingProfile, user.id) or Preferences()


@router.patch("/preferences", response_model=Preferences)
def save_preferences(payload: Preferences, db: DB, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    db.execute(select(User.id).where(User.id == user.id).with_for_update())
    profile = db.get(ShoppingProfile, user.id)
    if profile is None:
        profile = ShoppingProfile(user_id=user.id)
        db.add(profile)
    profile.categories = list(dict.fromkeys(payload.categories))
    profile.budget_inr = payload.budget_inr
    profile.keep_search_history = payload.keep_search_history
    if not payload.keep_search_history:
        db.execute(delete(SearchEvent).where(SearchEvent.user_id == user.id))
    db.commit()
    return profile


@router.get("/searches")
def search_history(db: DB, user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return list(db.scalars(select(SearchEvent.query).where(SearchEvent.user_id == user.id).order_by(SearchEvent.id.desc()).limit(30)))


@router.post("/searches", status_code=204)
def record_search(payload: SearchInput, db: DB, user: CurrentUser):
    db.execute(select(User.id).where(User.id == user.id).with_for_update())
    profile = db.get(ShoppingProfile, user.id)
    if not profile or not profile.keep_search_history:
        return
    rows = list(db.scalars(select(SearchEvent).where(SearchEvent.user_id == user.id).order_by(SearchEvent.id.desc())))
    query = payload.query.strip()
    if not rows or rows[0].query != query:
        db.add(SearchEvent(user_id=user.id, query=query))
        for row in rows[29:]:
            db.delete(row)
        db.commit()
