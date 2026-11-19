"""Verify the running development stack with a disposable shopper and Mailpit."""
import argparse
import json
import re
import secrets
import time
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener


def smoke(frontend, backend, inbox, *, live_openai=False):
    client = build_opener(HTTPCookieProcessor(CookieJar()))

    def request(root, path, *, method="GET", payload=None):
        headers = {"Origin": frontend} if root == frontend and method != "GET" else {}
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode()
        try:
            with client.open(Request(root + path, data=body, headers=headers, method=method), timeout=20) as response:
                return response.read().decode()
        except HTTPError as error:
            raise RuntimeError(f"{method} {path.split('?')[0]} returned HTTP {error.code}") from None

    def account(path, method="GET", payload=None):
        return request(frontend, "/api/account/" + path, method=method, payload=payload)

    def check(condition, description):
        if not condition:
            raise RuntimeError(description)
        print(description, flush=True)

    def email_token(email, purpose):
        query = urlencode({"query": "to:" + email})
        for _ in range(20):
            messages = json.loads(request(inbox, "/api/v1/search?" + query))["messages"]
            for message in messages:
                body = request(inbox, "/view/" + message["ID"] + ".txt")
                match = re.search(re.escape(frontend + "/account/" + purpose) + r"#token=([A-Za-z0-9_-]{43})(?![A-Za-z0-9_-])", body)
                if match:
                    return match[1]
            time.sleep(0.5)
        raise RuntimeError(f"Mailpit did not receive the {purpose} link")

    check(json.loads(request(backend, "/api/ready"))["status"] == "ready", "Database and backend are ready")
    products = json.loads(request(backend, "/api/products"))
    check(bool(products) and products[0]["title"].removeprefix("Sample ") in request(frontend, "/"), "Storefront renders API catalog products")
    check("Experiment history" in request(frontend, "/ml-evaluation"), "Experiment history renders")
    product_html = request(frontend, "/products/" + str(products[0]["id"]))
    check("https://www.amazon.in/s?" in product_html and "https://www.flipkart.com/search?" in product_html,
          "Product page provides both retailer search links")

    email = f"smoke-{secrets.token_hex(6)}@example.test"
    password = secrets.token_urlsafe(24)
    account("register", "POST", {"email": email, "password": password, "name": "Smoke Test"})
    account("login", "POST", {"email": email, "password": password})
    try:
        check(json.loads(account("me"))["email"] == email, "Registration and immediate sign-in work through the frontend")
        account("preferences", "PATCH", {"categories": ["Laptops"], "budget_inr": 65000, "keep_search_history": False})
        recommendations = json.loads(account("recommendations"))
        check(any(item["category"] == "Laptops" and item["price_inr"] <= 65000 for item in recommendations),
              "Personalized recommendations apply the saved category and budget")
        events = [json.loads(line) for line in account("assistant", "POST", {
            "question": "Find a laptop under INR 65,000",
        }).splitlines()]
        failure = next((entry["message"] for entry in events if entry["type"] == "error"), None)
        if failure:
            raise RuntimeError(failure)
        answer = "".join(entry["text"] for entry in events if entry["type"] == "delta")
        check(bool(answer) and ("Local catalog demo" not in answer if live_openai else "Local catalog demo" in answer)
              and events[-1]["type"] == "complete" and bool(events[-1]["products"]),
              "Live OpenAI assistant returned catalog products" if live_openai else "Local assistant streams a labeled catalog answer")
        account("forgot", "POST", {"email": email})
        replacement = secrets.token_urlsafe(24)
        account("reset", "POST", {"token": email_token(email, "reset"), "password": replacement})
        password = replacement
        account("login", "POST", {"email": email, "password": password})
        check(json.loads(account("me"))["email"] == email, "Mailpit password recovery and sign-in work")
    finally:
        try:
            account("login", "POST", {"email": email, "password": password})
            account("me", "DELETE", {"current_password": password})
        except (RuntimeError, URLError):
            print("The disposable smoke account could not be removed.", flush=True)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend", default="http://localhost:3000")
    parser.add_argument("--backend", default="http://127.0.0.1:8000")
    parser.add_argument("--inbox", default="http://127.0.0.1:8025")
    parser.add_argument("--live-openai", action="store_true", help="Expect a live OpenAI answer instead of the local demo")
    args = parser.parse_args()
    smoke(*(url.rstrip("/") for url in (args.frontend, args.backend, args.inbox)), live_openai=args.live_openai)


if __name__ == "__main__":
    main()
