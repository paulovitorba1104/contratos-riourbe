import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.routes import auth, health, usuarios
from app.core.boot_guard import validar_configuracao_producao
from app.core.config import get_settings
from app.middleware.body_size_limit import LimiteTamanhoCorpoMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

logger = logging.getLogger("riourbe")

settings = get_settings()
validar_configuracao_producao(settings)

app = FastAPI(title=settings.app_name)

app.add_middleware(SecurityHeadersMiddleware, settings=settings)
app.add_middleware(LimiteTamanhoCorpoMiddleware, max_bytes=settings.max_body_size_bytes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("IntegrityError em %s: %s", request.url.path, exc.orig)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Este registro conflita com dados já existentes no sistema."},
    )


app.include_router(health.router)
app.include_router(auth.router, prefix="/api")
app.include_router(usuarios.router, prefix="/api")


@app.get("/")
def raiz() -> dict:
    return {"sistema": settings.app_name, "ambiente": settings.ambiente}
