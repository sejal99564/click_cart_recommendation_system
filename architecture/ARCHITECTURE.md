# Shopwise AI architecture

| Component | Responsibility |
|---|---|
| Next.js | Server-rendered catalog, same-origin account proxy, shopping and admin views, assistant stream reader, and the report UI |
| FastAPI | Catalog queries, session and account operations, private collections and preferences, recommendation ranking, provider adapters, assistant tools, and role-checked admin operations |
| SQLAlchemy and Alembic | PostgreSQL in Docker and hosted configurations. SQLite is available for local development and tests. |
| Amazon and Flipkart adapters | Credential-gated, ephemeral provider searches with validated external product links |
| OpenAI Responses API | A server-side tool selection request followed by a streamed answer using catalog results |
| Experiment pipeline | Seeded synthetic interactions and merchant demand, model fitting and evaluation, persisted artifacts, and a downloadable report |

## Data relationships

- A user owns credentials, one shopping profile, collection items, recent searches, and conversations. Each conversation has ordered chat turns with a model name and token counts.
- Collection items reference persisted catalog products. A product can have many demo price snapshots. Admin edit events retain their action and resource ID, with the actor reference cleared if the account is deleted.
- Account deletion cascades to private data. Search history is opt-in and is cleared when disabled. A user can delete an individual conversation.
- Provider lookups and synthetic pricing are independent flows. Affiliate credentials and the OpenAI key stay in FastAPI. The assistant tool queries the stored demo catalog.

Browser requests use the frontend origin. Mutations require that configured origin and account requests use server-issued HTTP-only cookies. Deployment keeps the database and FastAPI upstream private. See the README for service health endpoints and release setup.
