"""StockEx API entry point.

Run with:  uvicorn app.main:app --reload
Then open: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Portfolio tracker for the Indian market (NSE).",
)

# A browser refuses to let a page on one origin call an API on another
# unless the API says it is allowed. The React dev server runs on port
# 5173, so without this every request from the front end fails with a
# CORS error that looks like a network fault.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health", tags=["meta"])
def health_check() -> dict[str, str]:
    """Liveness check. Deployment platforms ping this."""
    return {"status": "ok"}
