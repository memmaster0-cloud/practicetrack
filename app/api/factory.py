"""Фабрика приложения FastAPI."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..errors import DomainError
from .errors import status_for
from .routes import router

DESCRIPTION = (
    "REST API учёта сдачи практических работ. Для защищённых маршрутов сначала "
    "выполните POST /api/auth/login и нажмите Authorize, вставив полученный токен.")


def create_app(lifespan=None) -> FastAPI:
    app = FastAPI(title="ПрактикаТрек API", version="1.0.0", description=DESCRIPTION,
                  lifespan=lifespan)
    app.include_router(router)

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        return JSONResponse(status_code=status_for(exc), content={"detail": str(exc)})

    @app.get("/health", tags=["service"], summary="Проверка работоспособности")
    def health() -> dict:
        return {"status": "ok"}

    return app
