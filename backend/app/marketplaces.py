import logging
import os
import re
import time
from datetime import datetime, timezone
from threading import Lock
from typing import Literal, Protocol
from urllib.parse import parse_qs, urlsplit, urlunsplit
from unicodedata import normalize

import httpx
from fastapi import APIRouter, Query, Request, Response
from pydantic import BaseModel, Field

from .auth import limit

router = APIRouter(prefix="/api/marketplaces")
logger = logging.getLogger(__name__)


class Listing(BaseModel):
    id: str
    title: str
    brand: str | None = None
    category: str | None = None
    price: float | None = None
    currency: str | None = None
    availability: str | None = None
    marketplace: str
    source_url: str
    last_updated: datetime
    description: str | None = None
    features: list[str] = Field(default_factory=list)
    in_stock: bool | None = None


class Provider(Protocol):
    def configured(self) -> bool: ...
    def search(self, client: httpx.Client, query: str, observed: datetime) -> list[Listing]: ...


def product_link(raw: str, hosts: set[str], product_id: str, amazon: bool) -> str | None:
    try:
        url = urlsplit(raw)
        allowed_url = url.scheme in {"http", "https"} and url.hostname in hosts and url.port is None and not url.username and not url.password
        if not allowed_url:
            return None
        if amazon:
            if not re.fullmatch(r"[A-Z0-9]{10}", product_id) or not re.search(r"/dp/" + product_id + r"(?:/|$)", url.path):
                return None
        elif "/p/" not in url.path or parse_qs(url.query).get("pid") != [product_id]:
            return None
        return urlunsplit(("https", url.netloc, url.path, url.query, ""))
    except ValueError:
        return None


def amount(money):
    value = money.get("amount")
    if money.get("currency") == "INR" and type(value) in (float, int) and 0 <= value <= 10**9:
        return {"price": value, "currency": "INR"}
    return {}


class AmazonIndia:
    version_hosts = {"3.1": "api.amazon.com", "3.2": "api.amazon.co.uk", "3.3": "api.amazon.co.jp"}

    def __init__(self):
        self._lock = Lock()
        self._token = None
        self._expires = 0
        self._identity = None

    def configured(self):
        return all(os.getenv(key) for key in ("AMAZON_CREDENTIAL_ID", "AMAZON_CREDENTIAL_SECRET", "AMAZON_PARTNER_TAG")) and self.version() in self.version_hosts

    def version(self):
        return os.getenv("AMAZON_CREDENTIAL_VERSION", "3.2")

    def token(self, client):
        identity = (os.environ["AMAZON_CREDENTIAL_ID"], self.version())
        with self._lock:
            if self._token and self._identity == identity and time.monotonic() < self._expires:
                return self._token
            response = client.post(f"https://{self.version_hosts[identity[1]]}/auth/o2/token", json={
                "grant_type": "client_credentials", "client_id": identity[0],
                "client_secret": os.environ["AMAZON_CREDENTIAL_SECRET"], "scope": "creatorsapi::default",
            })
            response.raise_for_status()
            payload = response.json()
            self._token = payload["access_token"]
            self._expires = time.monotonic() + max(0, int(payload["expires_in"]) - 60)
            self._identity = identity
            return self._token

    def search(self, client, query, observed):
        response = client.post("https://creatorsapi.amazon/catalog/v1/searchItems", headers={
            "Authorization": "Bearer " + self.token(client), "x-marketplace": "www.amazon.in",
        }, json={
            "keywords": query, "marketplace": "www.amazon.in", "partnerTag": os.environ["AMAZON_PARTNER_TAG"],
            "resources": ["itemInfo.title", "itemInfo.byLineInfo", "itemInfo.classifications", "itemInfo.features",
                          "offersV2.listings.price", "offersV2.listings.availability", "offersV2.listings.violatesMAP"],
        })
        response.raise_for_status()
        listings = []
        for item in (response.json().get("searchResult") or {}).get("items", []):
            id_ = item.get("asin") or ""
            link = product_link(item.get("detailPageURL") or "", {"amazon.in", "www.amazon.in"}, id_, amazon=True)
            info = item.get("itemInfo") or {}
            title = (info.get("title") or {}).get("displayValue")
            if not link or not title:
                continue
            offer = next(iter((item.get("offersV2") or {}).get("listings") or []), {})
            price = {} if offer.get("violatesMAP") else amount((offer.get("price") or {}).get("money") or {})
            availability = offer.get("availability") or {}
            stock = {"IN_STOCK": True, "OUT_OF_STOCK": False}.get(availability.get("type"))
            listings.append(Listing(
                id=id_, title=title, brand=((info.get("byLineInfo") or {}).get("brand") or {}).get("displayValue"),
                category=((info.get("classifications") or {}).get("productGroup") or {}).get("displayValue"),
                marketplace="Amazon India", source_url=link, last_updated=observed,
                availability=availability.get("message"), in_stock=stock,
                features=((info.get("features") or {}).get("displayValues") or [])[:5], **price,
            ))
        return listings


class Flipkart:
    def configured(self):
        return bool(os.getenv("FLIPKART_AFFILIATE_ID") and os.getenv("FLIPKART_AFFILIATE_TOKEN"))

    def search(self, client, query, observed):
        response = client.get("https://affiliate-api.flipkart.net/affiliate/1.0/search.json",
                              params={"query": query, "resultCount": 10}, headers={
                                  "Fk-Affiliate-Id": os.environ["FLIPKART_AFFILIATE_ID"],
                                  "Fk-Affiliate-Token": os.environ["FLIPKART_AFFILIATE_TOKEN"],
                              })
        response.raise_for_status()
        listings = []
        for item in response.json().get("productInfoList", []):
            info = item.get("productBaseInfoV1") or {}
            id_ = info.get("productId") or ""
            link = product_link(info.get("productUrl") or "", {"flipkart.com", "www.flipkart.com", "dl.flipkart.com"}, id_, amazon=False)
            if not id_ or not link or not info.get("title"):
                continue
            stock = info.get("inStock")
            listings.append(Listing(
                id=id_, title=info["title"], brand=info.get("productBrand"), marketplace="Flipkart",
                source_url=link, last_updated=observed,
                availability="In stock" if stock is True else "Out of stock" if stock is False else None,
                in_stock=stock if isinstance(stock, bool) else None,
                description=(info.get("productDescription") or "")[:1200] or None,
                features=((item.get("categorySpecificInfoV1") or {}).get("keySpecs") or [])[:5],
                **amount(info.get("flipkartSpecialPrice") or info.get("flipkartSellingPrice") or {}),
            ))
        return listings


PROVIDERS: dict[str, Provider] = {"amazon": AmazonIndia(), "flipkart": Flipkart()}


def search_providers(query: str, provider: str | None = None):
    results = {}
    with httpx.Client(timeout=5, follow_redirects=False) as client:
        for key, adapter in PROVIDERS.items():
            if provider and key != provider:
                continue
            status, items = ("ready", []) if adapter.configured() else ("unconfigured", [])
            if status == "ready" and query:
                observed = datetime.now(timezone.utc)
                try:
                    items = adapter.search(client, query, observed)
                except (ValueError, TypeError, KeyError, AttributeError, httpx.HTTPError) as error:
                    status = "unavailable"
                    logger.warning("Marketplace %s request failed (%s)", key, type(error).__name__)
            results[key] = {"status": status, "listings": items}
    return results


@router.get("")
def marketplace_search(request: Request, response: Response, q: str = Query("", max_length=120),
                       provider: Literal["amazon", "flipkart"] | None = None):
    response.headers["Cache-Control"] = "no-store"
    query = q.strip()
    if query:
        limit(request, "marketplaces", 12)
    return search_providers(query, provider)


def distinct_listings(items: list[Listing]):
    groups: dict[tuple[str, str], dict[str, Listing]] = {}
    for item in items:
        brand = " ".join(normalize("NFKC", item.brand or "").casefold().split())
        title = " ".join(normalize("NFKC", item.title).casefold().split())
        if brand and title:
            groups.setdefault((brand, title), {})[item.id] = item
    return {key: next(iter(group.values())) for key, group in groups.items() if len(group) == 1}


@router.get("/matches")
def marketplace_matches(request: Request, response: Response, q: str = Query("", max_length=120)):
    response.headers["Cache-Control"] = "no-store"
    query = q.strip()
    if query:
        limit(request, "marketplaces", 12)
    results = search_providers(query)
    amazon = distinct_listings(results["amazon"]["listings"])
    flipkart = distinct_listings(results["flipkart"]["listings"])
    return {
        "providers": {key: value["status"] for key, value in results.items()},
        "matches": [
            {
                "title": amazon[key].title,
                "brand": amazon[key].brand,
                "amazon_url": amazon[key].source_url,
                "flipkart_url": flipkart[key].source_url,
            }
            for key in amazon if key in flipkart
        ],
    }
