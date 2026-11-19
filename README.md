# Shopwise AI

Shopwise AI combines a Next.js storefront, a FastAPI backend, PostgreSQL with Alembic migrations, and reproducible retail ML experiments. The local catalog contains four illustrative products. Authorized marketplace results come from separate live provider requests.

## Start on Windows with Docker Desktop

From the folder containing this README, open a VS Code PowerShell terminal and run:

```powershell
docker compose up --build
```

Open [Shopwise AI](http://localhost:3000) and [FastAPI docs](http://localhost:8000/docs). Create an account and sign in immediately, or continue as a guest to browse, compare, and save items in your browser. The [development email inbox](http://localhost:8025) receives password reset links. The Compose backend applies migrations automatically. Choose the same frontend hostname throughout the account flow.

## Run without Docker

Backend, in a PowerShell terminal:

```powershell
Set-Location backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

SQLite is the default for this local mode. Set `$env:DATABASE_URL` to a PostgreSQL SQLAlchemy URL before running migrations to use PostgreSQL. Configure SMTP for registration and password recovery. For a local Mailpit instance, use host `127.0.0.1`, port `1025`, a test sender address, and `SMTP_STARTTLS=false`.

If you keep local integration credentials in the project-root `.env`, start Uvicorn from `backend` with `.venv\Scripts\python.exe -m uvicorn app.main:app --env-file ../.env --reload`. Set `DATABASE_URL=sqlite:///./shopwise.db` in that file for the local preview. When switching databases, apply the migrations to the same database before launching the backend.

Frontend, in a second PowerShell terminal:

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run dev
```

The development server uses [localhost:3000](http://localhost:3000). `API_INTERNAL_URL` defaults to `http://localhost:8000` for local development. Set environment variables in the terminal or host configuration before launching the relevant service. Compose reads values from the root environment file, which is ignored by Git.

## Integrations

To use Gemini for shopping chat, set `SHOPPING_AI_PROVIDER=gemini`, add a Google AI Studio key as `GEMINI_API_KEY`, and set `GEMINI_MODEL=gemini-3.5-flash-lite` in the backend environment. Restart the backend after changing providers. Gemini uses the same catalog lookup, streaming interface, and conversation history. If the API is unavailable before an answer starts, the assistant can return a labeled catalog result. [Gemini API compatibility documentation](https://ai.google.dev/gemini-api/docs/openai)

Guests can chat and keep recent messages in their current tab. Signed-in shoppers can save conversations to their account. The demo catalog includes multiple phone, headphone, and laptop options with illustrative prices and specifications.

In a local development preview with no OpenAI credentials, the assistant uses a labeled catalog search for basic category, budget, and comparison requests. Product details and assistant results link to retailer search pages. Verified direct listing links are available through the separate marketplace adapters when authorized credentials are configured.

For Compose, copy `.env.example` to `.env` and configure the services you plan to use. Keep provider credentials and mail passwords in that local file or your deployment secret store.

- **OpenAI shopping assistant** requires backend-only `OPENAI_API_KEY` and `OPENAI_MODEL`. It streams answers, uses a structured tool to search or compare the persisted demo catalog, stores private conversations, and records completed-turn token usage. Signed-in shoppers can see their saved conversations. The assistant receives the shopper's question, recent turns, preferences, and relevant demo catalog records.
- **Amazon India** requires approved Creators API access, `AMAZON_CREDENTIAL_ID`, `AMAZON_CREDENTIAL_SECRET`, `AMAZON_CREDENTIAL_VERSION`, and `AMAZON_PARTNER_TAG`. [Amazon Creators API documentation](https://affiliate-program.amazon.in/creatorsapi/docs/en-us/introduction)
- **Flipkart** requires an approved affiliate ID and token configured as `FLIPKART_AFFILIATE_ID` and `FLIPKART_AFFILIATE_TOKEN`. [Flipkart Affiliate API documentation](https://affiliate.flipkart.com/api-docs/af_overview.html)
- Marketplace results appear at `/marketplaces` with source timestamps and provider product links. The demo catalog and assistant remain usable independently of affiliate access. Confirm your affiliate agreement and permitted display configuration before enabling a provider.
- Each retailer’s search displays its own price and availability. For discovery across both, choose **Find matches on both**. This shows links for unambiguous, exact brand-and-title matches and asks shoppers to confirm variants. Amazon India specifies additional conditions for cross-retailer price comparisons, including lowest new and used offers when supplied. [Amazon Associates linking requirements](https://affiliate-program.amazon.in/help/operating/linking)
- In Marketplace search, add two to four authorized listings to the shopping list and compare the supplied features and availability. Enter an important feature to highlight the only listing that explicitly lists it, if one exists. Use the retailer links for customer reviews and current prices.
- To grant administration, independently confirm the account owner’s identity and run `python -m app.promote_admin <email> --confirm-owner` from the backend environment. Admins can edit demo listings and see aggregate account and assistant usage data.
- To show an assistant cost estimate, set `OPENAI_ESTIMATE_INPUT_USD_PER_MILLION` and `OPENAI_ESTIMATE_OUTPUT_USD_PER_MILLION` for the configured model. The estimate uses the token totals recorded for completed turns.

## Tests and experiments

- With the development Compose stack running, run `python scripts/smoke_preview.py` from the project root. It checks the catalog, retailer search links, experiment history, account creation, immediate sign-in, password recovery through Mailpit, recommendations, and the local catalog assistant. It creates a disposable test account. Run this against a development stack with the OpenAI variables unset.

- Run `python -m pytest tests -q` from the backend folder. Set `SHOPWISE_TEST_DATABASE_URL` to a dedicated empty PostgreSQL test database to validate migrations and API behavior against PostgreSQL. Tests create and drop isolated schemas there.
- Run `npm.cmd run build` from the frontend folder for the production compile and type checks.
- For browser tests, build the frontend first. Install `requirements-e2e.txt` in the backend environment and install Playwright Chromium with `python -m playwright install chromium`. Set `SHOPWISE_BROWSER_TESTS=1` and run `python -m pytest tests/test_browser.py -q` from the backend folder. The test uses a temporary database, delivers password reset mail to a loopback SMTP inbox, and mocks the assistant and marketplaces.
- From the project root, install `ml/requirements.txt`, then run `python -m ml.run_experiments --seed 42`. Each run writes an archived report under `frontend/public/experiment-runs` and model artifacts in a folder with the same run ID under `models/artifacts`. It also refreshes the latest report. Rebuild the frontend to publish the updated dashboard and pricing model. Run `python -m pytest ml/tests -q` with pytest installed to verify the results.
- The UI exposes the paper's reported results at `/research`, synthetic outcomes at `/ml-evaluation`, and an interactive simulated merchant estimate at `/pricing-lab`. See [research/RESEARCH_ALIGNMENT.md](research/RESEARCH_ALIGNMENT.md) for reproduction requirements and experimental deviations.

## Deployment configuration

Run `backend/.venv/Scripts/python.exe scripts/check_production.py` from the project root on Windows to check the production settings. The command reports missing or malformed settings without displaying credential values. It checks configuration only.

Build the frontend and backend images from their respective folders. Point the backend at managed PostgreSQL using a runtime secret. Apply `alembic upgrade head` once as a release task before starting workers. Use `/api/health` for liveness and `/api/ready` for database readiness.

Set `APP_ENV=production`, `FRONTEND_ORIGIN` to the exact HTTPS user-facing origin, and configure a production SMTP host, port and sender with STARTTLS. Set the frontend's server-only `API_INTERNAL_URL` to the private backend address. The Next.js server forwards account requests and secure cookies on the same browser origin. Expose the frontend through HTTPS, keep the database and FastAPI upstream private, and configure ingress request-size limits and shared rate limits for account and provider routes. The app also applies process-local quotas; those quotas are per instance and unauthenticated requests behind the same upstream share an application limit. Configure any proxy in front of the assistant to stream response chunks without buffering.

Live OpenAI, SMTP and affiliate behavior requires environment-specific verification before launch. The bundled Compose stack is for local development.
