import json
from contextlib import nullcontext
from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient

from app import assistant, auth
from app.main import app
from app.marketplaces import AmazonIndia, Flipkart


def fake_openai(monkeypatch):
    calls = []
    usage = SimpleNamespace(input_tokens=20, output_tokens=5)
    final_text = "The sample Everyday Laptop has 16 GB of memory."
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    def create(**kwargs):
        calls.append(kwargs)
        if not kwargs.get("stream"):
            item = SimpleNamespace(
                type="function_call", name="lookup_catalog", call_id="call_test",
                arguments='{"query":"laptop","budget":65000,"ids":[]}',
            )
            return SimpleNamespace(output=[item], usage=usage)
        completed = SimpleNamespace(output_text=final_text, usage=usage)
        return nullcontext(iter([
            SimpleNamespace(type="response.output_text.delta", delta=final_text),
            SimpleNamespace(type="response.completed", response=completed),
        ]))

    monkeypatch.setattr(assistant, "openai_client", lambda _key: nullcontext(SimpleNamespace(responses=SimpleNamespace(create=create))))
    return calls


def register_and_login(client, email):
    credentials = {"email": email, "password": "test-account-passphrase"}
    assert client.post("/api/auth/register", json={**credentials, "name": "Test Shopper"}).status_code == 201
    assert client.post("/api/auth/login", json=credentials).status_code == 204


def test_shopping_assistant_stream_and_conversation_privacy(monkeypatch):
    calls = fake_openai(monkeypatch)
    with TestClient(app, headers={"Origin": auth.ORIGIN}) as shopper:
        register_and_login(shopper, "first@example.test")
        response = shopper.post("/api/auth/assistant", json={"question": "Find a laptop under INR 65000"})
        assert response.status_code == 200
        status, delta, complete = [json.loads(line) for line in response.text.splitlines()]
        assert status["type"] == "status" and delta["type"] == "delta"
        assert complete["type"] == "complete" and [p["id"] for p in complete["products"]] == [1, 7, 8]
        assert calls[0]["tool_choice"] == "required"
        assert calls[1]["input"][-1]["call_id"] == "call_test"
        chat = shopper.get("/api/auth/conversations", params={"id": complete["id"]}).json()
        assert chat[0]["answer"] == delta["text"]
        assert shopper.get("/api/auth/admin").status_code == 403
        with TestClient(app, headers={"Origin": auth.ORIGIN}) as other:
            register_and_login(other, "other@example.test")
            assert other.get("/api/auth/conversations", params={"id": complete["id"]}).status_code == 404
            assert other.delete("/api/auth/conversations", params={"id": complete["id"]}).status_code == 404
        assert shopper.delete("/api/auth/conversations", params={"id": complete["id"]}).status_code == 204
        assert shopper.get("/api/auth/conversations").json() == []


def test_collections_and_opt_in_search_history(monkeypatch):
    with TestClient(app, headers={"Origin": auth.ORIGIN}) as shopper:
        register_and_login(shopper, "first@example.test")
        change = {"kind": "wishlist", "product_id": 1, "selected": True}
        assert shopper.patch("/api/auth/collections", json=change).json()["wishlist"] == [1]
        assert shopper.patch("/api/auth/collections", json=change).json()["wishlist"] == [1]
        assert shopper.post("/api/auth/searches", json={"query": "laptop"}).status_code == 204
        assert shopper.get("/api/auth/searches").json() == []
        preferences = {"categories": ["Laptops"], "budget_inr": 65000, "keep_search_history": True}
        assert shopper.patch("/api/auth/preferences", json=preferences).status_code == 200
        assert {item["id"] for item in shopper.get("/api/auth/recommendations").json()} == {7, 8}
        assert shopper.patch("/api/auth/preferences", json={**preferences, "budget_inr": 70000}).status_code == 200
        assert {item["id"] for item in shopper.get("/api/auth/recommendations").json()} == {4, 7, 8}
        assert shopper.post("/api/auth/searches", json={"query": "laptop"}).status_code == 204
        with TestClient(app, headers={"Origin": auth.ORIGIN}) as other:
            register_and_login(other, "other@example.test")
            assert other.get("/api/auth/collections").json()["wishlist"] == []
            assert other.get("/api/auth/searches").json() == []
        assert shopper.get("/api/auth/searches").json() == ["laptop"]
        assert shopper.patch("/api/auth/preferences", json={**preferences, "keep_search_history": False}).status_code == 200
        assert shopper.get("/api/auth/searches").json() == []


def test_marketplace_adapters_use_authorized_endpoints_and_omit_invalid_links(monkeypatch):
    from datetime import datetime, timezone

    for name in ("AMAZON_CREDENTIAL_ID", "AMAZON_CREDENTIAL_SECRET", "AMAZON_PARTNER_TAG",
                 "FLIPKART_AFFILIATE_ID", "FLIPKART_AFFILIATE_TOKEN"):
        monkeypatch.setenv(name, "test-only")
    def respond(request):
        if request.url.path == "/auth/o2/token":
            assert request.url.host == "api.amazon.co.uk"
            return httpx.Response(200, json={"access_token": "fake", "expires_in": 3600})
        if request.url.host == "creatorsapi.amazon":
            assert request.headers["x-marketplace"] == "www.amazon.in"
            item = {
                "asin": "B000000001", "detailPageURL": "https://www.amazon.in/dp/B000000001?tag=test",
                "itemInfo": {"title": {"displayValue": "Amazon demo listing"}},
                "offersV2": {"listings": [{"price": {"money": {"amount": 2999, "currency": "INR"}}}]},
            }
            return httpx.Response(200, json={"searchResult": {"items": [item, dict(item, detailPageURL="https://example.test/dp/B000000001")]}})
        assert request.url.host == "affiliate-api.flipkart.net"
        assert request.headers["Fk-Affiliate-Token"] == "test-only"
        return httpx.Response(200, json={"productInfoList": [{"productBaseInfoV1": {
            "productId": "ABC123", "title": "Flipkart demo listing", "inStock": True,
            "productUrl": "http://dl.flipkart.com/dl/example/p/123?pid=ABC123",
            "flipkartSpecialPrice": {"amount": 2500, "currency": "INR"},
        }}]})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        instant = datetime.now(timezone.utc)
        amazon = AmazonIndia().search(client, "headphones", instant)
        flipkart = Flipkart().search(client, "headphones", instant)
    assert len(amazon) == 1 and amazon[0].price == 2999
    assert len(flipkart) == 1 and flipkart[0].price == 2500 and flipkart[0].availability == "In stock"
    assert flipkart[0].source_url.startswith("https://dl.flipkart.com/")

def test_admin_can_update_demo_catalog_and_record_the_change(monkeypatch, migrated_database):
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from app.models import AuditEvent, User

    with TestClient(app, headers={"Origin": auth.ORIGIN}) as client:
        register_and_login(client, "admin@example.test")
        payload = {"id": 1, "price_inr": 48000, "description": "Revised demo listing"}
        assert client.patch("/api/auth/admin", json=payload).status_code == 403
        with Session(migrated_database) as db:
            user = db.scalar(select(User).where(User.email == "admin@example.test"))
            user.role = "admin"
            db.commit()
        assert client.patch("/api/auth/admin", json=payload).status_code == 200
        assert client.patch("/api/auth/admin", json=payload).status_code == 200
        assert client.get("/api/products/1").json()["price_inr"] == 48000
        history = client.get("/api/products/1/prices").json()
        assert history["data_status"] == "sample"
        assert [entry["price_inr"] for entry in history["snapshots"]] == [48000]
        assert client.get("/api/auth/admin").json()["catalog_audit_events"] == 1
        with Session(migrated_database) as db:
            assert db.scalar(select(AuditEvent)).action == "catalog.demo.update"

def test_marketplace_matching_excludes_ambiguous_variants_and_prices(monkeypatch):
    from datetime import datetime, timezone
    from app import marketplaces

    def listing(id_, title, brand, url):
        return marketplaces.Listing(id=id_, title=title, brand=brand, marketplace="Test",
                                    source_url=url, price=2499, last_updated=datetime.now(timezone.utc))

    amazon = listing("1", "Example Headset 2 Black", "Example", "https://www.amazon.in/dp/B000000001")
    similar = listing("2", "Example Headset 2 White", "Example", "https://www.amazon.in/dp/B000000002")
    flipkart = listing("3", "example  headset 2 black", "example", "https://www.flipkart.com/example/p/3?pid=3")
    ambiguous = similar.model_copy(update={"id": "4"})
    payload = {
        "amazon": {"status": "ready", "listings": [amazon, similar, ambiguous]},
        "flipkart": {"status": "ready", "listings": [flipkart, similar]},
    }
    monkeypatch.setattr(marketplaces, "search_providers", lambda query: payload)
    with TestClient(app) as client:
        response = client.get("/api/marketplaces/matches", params={"q": "Example Headset 2"})
    assert response.status_code == 200
    assert response.json()["matches"] == [{
        "title": amazon.title, "brand": amazon.brand, "amazon_url": amazon.source_url,
        "flipkart_url": flipkart.source_url,
    }]
    assert response.headers["Cache-Control"] == "no-store"

def test_local_assistant_returns_catalog_matches_without_openai(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setenv("APP_ENV", "development")
    with TestClient(app, headers={"Origin": auth.ORIGIN}) as shopper:
        register_and_login(shopper, "local@example.test")
        response = shopper.post("/api/auth/assistant", json={"question": "Find a laptop under INR 65,000"})
        assert response.status_code == 200
        _, delta, complete = [json.loads(line) for line in response.text.splitlines()]
        assert "Local catalog demo" in delta["text"]
        assert [product["id"] for product in complete["products"]] == [1, 7, 8]
        assert shopper.get("/api/auth/conversations", params={"id": complete["id"]}).json()[0]["answer"] == delta["text"]
        monkeypatch.setenv("APP_ENV", "production")
        assert shopper.post("/api/auth/assistant", json={"question": "Find a phone"}).status_code == 503


def test_assistant_uses_catalog_when_openai_credits_are_exhausted(monkeypatch):
    import httpx
    from openai import RateLimitError

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    def exhausted(_key):
        response = httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
        raise RateLimitError("No API credits", response=response, body={"code": "credit_balance_exhausted"})

    monkeypatch.setattr(assistant, "openai_client", exhausted)
    with TestClient(app, headers={"Origin": auth.ORIGIN}) as shopper:
        register_and_login(shopper, "quota@example.test")
        response = shopper.post("/api/auth/assistant", json={"question": "please tell me better smartphone to buy"})
        assert response.status_code == 200
        _, delta, complete = [json.loads(line) for line in response.text.splitlines()]
        assert "Local catalog demo" in delta["text"] and "credits are exhausted" in delta["text"]
        assert [product["category"] for product in complete["products"]] == ["Phones"] * 3
        history = shopper.get("/api/auth/conversations", params={"id": complete["id"]}).json()
        assert history[0]["answer"] == delta["text"]

def test_gemini_uses_catalog_tool_then_streams_grounded_answer(monkeypatch, migrated_database):
    from openai import OpenAI
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from app.models import ChatTurn

    requests = []

    def upstream(request):
        assert request.url.host == "generativelanguage.googleapis.com"
        assert request.url.path == "/v1beta/openai/chat/completions"
        assert request.headers["authorization"] == "Bearer test-gemini-key"
        payload = json.loads(request.content)
        requests.append(payload)
        common = {"id": "gemini-test", "created": 1, "model": payload["model"]}
        usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        if not payload.get("stream"):
            return httpx.Response(200, json={**common, "object": "chat.completion", "usage": usage, "choices": [{
                "index": 0, "finish_reason": "tool_calls", "message": {"role": "assistant", "tool_calls": [{
                    "id": "lookup", "type": "function", "function": {
                        "name": "lookup_catalog", "arguments": '{"query":"smartphone","budget":null,"ids":[]}',
                    },
                }]},
            }]})
        chunks = [
            {**common, "object": "chat.completion.chunk", "choices": [
                {"index": 0, "delta": {"content": "The demo catalog has one smartphone."}, "finish_reason": "stop"},
            ]},
            {**common, "object": "chat.completion.chunk", "choices": [], "usage": usage},
        ]
        return httpx.Response(200, headers={"Content-Type": "text/event-stream"},
                              text="".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks) + "data: [DONE]\n\n")

    monkeypatch.setenv("SHOPPING_AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setattr(assistant, "gemini_client", lambda key: OpenAI(
        api_key=key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        http_client=httpx.Client(transport=httpx.MockTransport(upstream)), max_retries=0,
    ))
    with TestClient(app, headers={"Origin": auth.ORIGIN}) as shopper:
        register_and_login(shopper, "gemini@example.test")
        response = shopper.post("/api/auth/assistant", json={"question": "Suggest a smartphone"})
    _, delta, complete = [json.loads(line) for line in response.text.splitlines()]
    assert delta["type"] == "delta" and "one smartphone" in delta["text"]
    assert [product["id"] for product in complete["products"]] == [2, 9, 10]
    assert requests[0]["tool_choice"]["function"]["name"] == "lookup_catalog"
    grounded = json.loads(requests[1]["messages"][-1]["content"])
    assert [item["id"] for item in grounded["catalog_records"]] == [2, 9, 10]
    with Session(migrated_database) as db:
        turn = db.scalar(select(ChatTurn))
        assert (turn.model, turn.input_tokens, turn.output_tokens) == ("gemini-3.5-flash-lite", 20, 10)

def test_guest_assistant_returns_multiple_options_without_storing_a_conversation(monkeypatch, migrated_database):
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from app.models import Conversation

    monkeypatch.setenv("SHOPPING_AI_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "development")
    with TestClient(app, headers={"Origin": auth.ORIGIN}) as guest:
        result = guest.post("/api/auth/assistant", json={"question": "I need wrieless headphones under ₹6,000"})
        assert result.status_code == 200
        complete = json.loads(result.text.splitlines()[-1])
        assert complete["id"] is None
        assert [item["id"] for item in complete["products"]] == [3, 5, 6]
        assert guest.get("/api/auth/conversations").status_code == 401
    with Session(migrated_database) as db:
        assert db.scalar(select(Conversation.id)) is None
