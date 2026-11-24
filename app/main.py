from fastapi import FastAPI

from app.api.errors import register_exception_handler
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)
register_exception_handler(app)
app.include_router(api_router)


@app.get("/")
def root():
    return {"message": "Hello from fast api"}
