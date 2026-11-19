# Instructions for Gemini / Antigravity

You are taking over this repository as a senior full-stack + ML engineer. Read README.md, `research/RESEARCH_ALIGNMENT.md`, and the original research paper supplied by the user before implementing features. Keep the project as a **new** project, separate from the previous Streamlit application.

## Goal
Turn this working scaffold into a real-world AI retail intelligence platform using Next.js, TypeScript, Tailwind, FastAPI, PostgreSQL, SQLAlchemy/Alembic, scikit-learn, and server-side OpenAI API integration.

## Non-negotiable features
1. Secure user registration/login/logout, password reset, session management, role-based authorization, profiles.
2. Real persistent database: users, preferences, products, source listings, interaction events, wishlists, conversations, experiments, evaluation metrics, price snapshots.
3. Authorized Amazon/Flipkart product data adapters, with verified product redirects. Do not scrape without authorization. Fall back to clearly labeled local catalog data when API access is unavailable.
4. Personalized recommendations using paper-aligned content-based/collaborative/hybrid algorithms, with actual training and metrics (Precision@K, Recall@K, NDCG@K, MAP@K as applicable).
5. OpenAI shopping assistant using official SDK and server-side credentials; tool calls must query the real catalog; no invented prices or specs.
6. Product comparison with explainable tradeoffs.
7. Dynamic pricing **only for a simulated or merchant-controlled catalog**, never change Amazon/Flipkart prices; real experiments with appropriate regression/business metrics.
8. ML/research dashboard: paper-reported vs reproduced vs new results, real experiment artifacts, clear reproducibility limitations.
9. Customer dashboard and admin analytics, responsive production-quality UI.
10. Tests, Docker, migrations, CI, deployment instructions, secret handling, rate limits, privacy safeguards.

## Implementation order
- Phase 0: Read the source PDF, extract exact paper methodology, datasets, models, evaluation metrics, and reported results. Update `research/RESEARCH_ALIGNMENT.md` with evidence and gaps. Do not invent figures.
- Phase 1: Database schema + Alembic, authentication, secure sessions, API tests.
- Phase 2: Catalog and product comparison UI/API, provider interface, authorized source integrations and verified redirects.
- Phase 3: ML pipelines, reproducible datasets/splits/training/evaluation and saved experiment runs.
- Phase 4: OpenAI assistant with product search/compare tools and persistent conversations.
- Phase 5: Pricing lab, customer/admin dashboards, research comparison visualizations.
- Phase 6: End-to-end tests, observability, deployment and docs.

## Quality bar
Do not build fake buttons, static pretend dashboards, fabricated model scores, fake live pricing, fake auth, or placeholder API integrations represented as finished. Keep the existing health/catalog demo operational while iterating. Run tests at the end of each phase. Clearly state blockers requiring API credentials or unavailable datasets. Commit small, working changes.

## Immediate task
Inspect the repo, read the research paper, produce a concrete architecture + ERD + traceability table, then implement Phase 1. Ask the user for external credentials only when needed; never request credentials to be pasted into source code.
