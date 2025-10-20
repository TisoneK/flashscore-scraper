import logging
from fastapi import FastAPI
from .routes import jobs, results, scraper


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Flashscore Scraper API", version="0.1.0")

    # Include routers
    app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
    app.include_router(results.router, prefix="/results", tags=["results"])
    app.include_router(scraper.router, prefix="/scraper", tags=["scraper"])

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()


