from fastapi import FastAPI

from app.api.errors import register_exception_handler
from app.api.middleware import log_requests
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging

app = FastAPI(title=settings.app_name, debug=settings.debug)
register_exception_handler(app)
setup_logging(settings.debug)
app.include_router(api_router)
app.middleware("http")(log_requests)


@app.get("/")
def root():
    return {"message": "Hello from fast api"}
