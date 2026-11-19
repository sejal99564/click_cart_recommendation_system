import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from .auth import DB, allowed_frontend_origins, router as auth_router
from .assistant import router as assistant_router
from .catalog import router as catalog_router
from .collections import router as collections_router
from .marketplaces import router as marketplaces_router
from .preferences import router as preferences_router
from .recommendations import router as recommendations_router
from .models import CatalogProduct

app = FastAPI(title="AI Retail Intelligence API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_frontend_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)
app.include_router(auth_router)
app.include_router(assistant_router)
app.include_router(catalog_router)
app.include_router(collections_router)
app.include_router(marketplaces_router)
app.include_router(preferences_router)
app.include_router(recommendations_router)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    if request.url.path.startswith("/api/auth/"):
        entries = [{"loc": item["loc"], "msg": item["msg"], "type": item["type"]} for item in error.errors()]
        return JSONResponse({"detail": entries}, status_code=422, headers={"Cache-Control": "no-store"})
    return await request_validation_exception_handler(request, error)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": app.version, "catalog_mode": "sample"}


@app.get("/api/ready")
def readiness(db: DB):
    try:
        db.execute(select(CatalogProduct.id).limit(1))
    except SQLAlchemyError as error:
        raise HTTPException(503, "Database unavailable") from error
    return {"status": "ready"}
