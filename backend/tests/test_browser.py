import os
import shutil
import socket
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from email import policy
from email.parser import BytesParser
from queue import Queue
from urllib.error import URLError
from urllib.request import urlopen

import pytest
import uvicorn

from app import auth
from app.main import app
from app.marketplaces import Listing, PROVIDERS
from test_shopping import fake_openai

pytestmark = pytest.mark.skipif(os.getenv("SHOPWISE_BROWSER_TESTS") != "1", reason="Set SHOPWISE_BROWSER_TESTS=1 after building the frontend")


def wait_http(url):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, URLError):
            time.sleep(0.2)
    raise RuntimeError(f"Server did not respond at {url}")


@pytest.fixture
def email_inbox(monkeypatch):
    from aiosmtpd.controller import Controller

    messages = Queue()

    class Inbox:
        async def handle_DATA(self, server, session, envelope):
            message = BytesParser(policy=policy.default).parsebytes(envelope.original_content)
            messages.put(message)
            return "250 Message stored"

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    service = Controller(Inbox(), hostname="127.0.0.1", port=port)
    service.start()
    try:
        monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
        monkeypatch.setenv("SMTP_PORT", str(port))
        monkeypatch.setenv("SMTP_FROM", "shopwise@example.test")
        monkeypatch.setenv("SMTP_STARTTLS", "false")
        monkeypatch.delenv("SMTP_USERNAME", raising=False)
        yield messages
    finally:
        service.stop()


def test_register_shop_compare_chat_and_open_store(monkeypatch, email_inbox):
    from playwright.sync_api import expect, sync_playwright

    root = Path(__file__).resolve().parents[2]
    frontend_root = root / "frontend"
    if not (frontend_root / ".next" / "BUILD_ID").is_file():
        pytest.fail("Build the Next.js production bundle before running this test")

    class TestAffiliate:
        def __init__(self, marketplace, url):
            self.marketplace = marketplace
            self.url = url

        def configured(self):
            return True

        def search(self, _client, _query, observed: datetime):
            return [Listing(
                id="B000000001", title="Mock affiliate laptop", brand="Mock Brand", marketplace=self.marketplace,
                source_url=self.url, last_updated=observed,
                price=49999, currency="INR",
                features=["Backlit keyboard"] if self.marketplace == "Amazon India" else ["Matte display"],
            )]

    monkeypatch.setitem(PROVIDERS, "amazon", TestAffiliate("Amazon India", "https://www.amazon.in/dp/B000000001?tag=demo"))
    monkeypatch.setitem(PROVIDERS, "flipkart", TestAffiliate("Flipkart", "https://www.flipkart.com/laptop/p/demo?pid=B000000001"))
    fake_openai(monkeypatch)
    with socket.socket() as backend_socket:
        backend_socket.bind(("127.0.0.1", 0))
        backend_port = backend_socket.getsockname()[1]
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            frontend_port = probe.getsockname()[1]
        origin = f"http://127.0.0.1:{frontend_port}"
        monkeypatch.setattr(auth, "ORIGIN", origin)
        backend = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
        thread = threading.Thread(target=backend.run, kwargs={"sockets": [backend_socket]}, daemon=True)
        thread.start()
        frontend = None
        try:
            wait_http(f"http://127.0.0.1:{backend_port}/api/health")
            frontend = subprocess.Popen(
                [shutil.which("node") or "node", "node_modules/next/dist/bin/next", "start", "--hostname", "127.0.0.1", "--port", str(frontend_port)],
                cwd=frontend_root, env={**os.environ, "API_INTERNAL_URL": f"http://127.0.0.1:{backend_port}"},
            )
            wait_http(origin + "/research")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=os.getenv("SHOPWISE_CHROMIUM_PATH") or None)
                try:
                    context = browser.new_context()
                    context.route("https://www.amazon.in/**", lambda route: route.fulfill(status=200, body="Mock retailer"))
                    page = context.new_page()
                    email = "browser-shopper@example.test"
                    password = "browser-test-password"
                    page.goto(origin + "/account/login")
                    page.get_by_role("link", name="Continue as guest").click()
                    guest_wishlist = page.get_by_role("button", name="Wishlist: Sample Camera Smartphone")
                    guest_wishlist.click()
                    expect(guest_wishlist).to_have_attribute("aria-pressed", "true")
                    page.wait_for_function("JSON.parse(localStorage.getItem('shopwise-collections') || '{}').wishlist?.includes(2)")
                    page.goto(origin + "/account/register")
                    page.get_by_label("Name", exact=True).fill("Browser Shopper")
                    page.get_by_label("Email", exact=True).fill(email)
                    page.get_by_label("Password", exact=True).fill(password)
                    page.get_by_role("button", name="Create an account").click()
                    expect(page.get_by_role("status")).to_have_text("Account created. You can now sign in.")
                    assert email_inbox.empty()
                    page.get_by_role("link", name="Sign in").click()
                    page.get_by_role("link", name="Forgot password?").click()
                    page.wait_for_url("**/account/forgot")
                    expect(page.get_by_role("heading", name="Reset your password")).to_be_visible()
                    expect(page.get_by_role("button", name="Send reset link")).to_be_enabled()
                    page.get_by_label("Email", exact=True).fill(email)
                    with page.expect_response(lambda response: "/api/account/forgot" in response.url, timeout=10000) as recovery:
                        page.get_by_role("button", name="Send reset link").click()
                    assert recovery.value.status == 202, recovery.value.text()
                    expect(page.get_by_role("status")).to_contain_text("receive a reset link")
                    reset_email = email_inbox.get(timeout=5)
                    reset_link = reset_email.get_body().get_content().splitlines()[0].removeprefix("Continue at ")
                    assert reset_link.startswith(origin + "/account/reset#token=")
                    page.goto(reset_link)
                    password = "browser-replaced-password"
                    page.get_by_label("New password", exact=True).fill(password)
                    page.get_by_role("button", name="Choose a new password").click()
                    expect(page.get_by_role("status")).to_have_text("Password updated. You can now sign in.")
                    page.get_by_role("link", name="Sign in").click()
                    page.get_by_label("Email", exact=True).fill(email)
                    page.get_by_label("Password", exact=True).fill(password)
                    page.get_by_role("button", name="Sign in").click()
                    expect(page.get_by_role("heading", name="Your account")).to_be_visible()
                    expect(page.get_by_text(email, exact=True)).to_be_visible()

                    page.get_by_role("link", name="Back to catalog").click()
                    expect(page.get_by_role("heading", name="Camera Smartphone")).to_be_visible()
                    expect(guest_wishlist).to_have_attribute("aria-pressed", "true")
                    page.wait_for_function("localStorage.getItem('shopwise-collections') === null")
                    page.get_by_label("Search products").fill("laptop")
                    page.get_by_label("Search products").press("Enter")
                    expect(page.get_by_role("heading", name="Gaming Laptop")).to_be_visible()
                    expect(page.get_by_role("heading", name="Camera Smartphone")).to_have_count(0)
                    page.get_by_label("Price", exact=True).select_option("50000")
                    expect(page.get_by_role("heading", name="Gaming Laptop")).to_have_count(0)
                    page.get_by_role("button", name="Clear filters").click()

                    everyday = page.get_by_role("button", name="Compare: Sample Everyday Laptop")
                    everyday.click()
                    expect(everyday).to_have_attribute("aria-pressed", "true")
                    gaming = page.get_by_role("button", name="Compare: Sample Gaming Laptop")
                    gaming.click()
                    expect(gaming).to_have_attribute("aria-pressed", "true")
                    page.get_by_role("button", name="Compare (2)", exact=True).click()
                    expect(page.get_by_role("table")).to_contain_text("16 GB")
                    page.get_by_role("link", name="Ask the assistant to explain the trade-offs").click()
                    expect(page.get_by_label("Your question")).to_have_value("Compare catalog products 4,1 and explain their trade-offs.")
                    page.get_by_role("button", name="Send").click()
                    expect(page.get_by_text("The sample Everyday Laptop has 16 GB of memory.")).to_be_visible()
                    expect(page.locator('a[href="https://www.amazon.in/s?k=Everyday+Laptop"]')).to_be_visible()
                    expect(page.locator('a[href="https://www.flipkart.com/search?q=Everyday+Laptop"]')).to_be_visible()
                    page.get_by_role("link", name="Sample Everyday Laptop").click()
                    expect(page.get_by_role("heading", name="Sample Everyday Laptop")).to_be_visible()

                    page.get_by_role("link", name="Back to catalog").click()
                    page.get_by_role("link", name="Marketplaces").click()
                    page.get_by_label("Product name").fill("laptop")
                    page.get_by_role("button", name="Search marketplaces").click()
                    with page.expect_popup() as popup:
                        page.get_by_role("link", name="View on Amazon India").click()
                    popup.value.wait_for_load_state()
                    assert popup.value.url.startswith("https://www.amazon.in/dp/B000000001")
                    page.get_by_role("button", name="Add to shopping list").click()
                    page.get_by_label("Marketplace").select_option("flipkart")
                    page.get_by_role("button", name="Search marketplaces").click()
                    expect(page.get_by_role("link", name="View on Flipkart")).to_be_visible()
                    page.get_by_role("button", name="Add to shopping list").click()
                    page.get_by_label("Feature you care about", exact=False).fill("backlit keyboard")
                    page.get_by_role("button", name="Compare saved listings").click()
                    expect(page.get_by_role("status")).to_contain_text("only listing that explicitly mentions")
                    page.get_by_label("Marketplace").select_option("matches")
                    page.get_by_role("button", name="Search marketplaces").click()
                    expect(page.get_by_role("heading", name="Listings with the same brand and title")).to_be_visible()
                    expect(page.get_by_role("link", name="View on Flipkart")).to_be_visible()

                    page.goto(origin + "/ml-evaluation")
                    expect(page.get_by_role("heading", name="Experiment history")).to_be_visible()
                    page.get_by_role("link", name="Seed 43").click()
                    expect(page.get_by_text("Synthetic experiment synthetic-v1 · Seed 43", exact=False)).to_be_visible()
                    download_url = page.get_by_role("link", name="Download results").get_attribute("href")
                    assert page.request.get(origin + download_url).json()["seed"] == 43
                    page.set_viewport_size({"width": 390, "height": 844})
                    page.goto(origin)
                    expect(page.get_by_role("heading", name="Explore products")).to_be_visible()
                    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                finally:
                    browser.close()
        finally:
            if frontend:
                frontend.terminate()
                frontend.wait(timeout=10)
            backend.should_exit = True
            thread.join(timeout=10)
