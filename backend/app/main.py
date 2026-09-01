import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from app.api.routes import atas_registro_preco, auth, contratos, fornecedores, health, modelos_ripm, usuarios
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
app.include_router(fornecedores.router, prefix="/api")
app.include_router(modelos_ripm.router, prefix="/api")
app.include_router(atas_registro_preco.router, prefix="/api")
app.include_router(contratos.router, prefix="/api")

# Em produção (imagem Railway), o build do frontend é copiado para app/static
# no momento do build da imagem — ver Dockerfile na raiz do repositório. Um
# único serviço serve API e SPA, evitando CORS/cookies cross-origin entre
# dois deploys (seção 2 do plano: "monólito modular — um backend, um deploy").
STATIC_DIR = Path(__file__).resolve().parent / "static"

if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{caminho_completo:path}", include_in_schema=False)
    def frontend_spa(caminho_completo: str) -> FileResponse:
        if caminho_completo.startswith("api/") or caminho_completo == "api":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rota da API não encontrada.")

        candidato = (STATIC_DIR / caminho_completo).resolve()
        dentro_do_static = candidato.is_relative_to(STATIC_DIR.resolve())
        if caminho_completo and dentro_do_static and candidato.is_file():
            return FileResponse(candidato)
        return FileResponse(STATIC_DIR / "index.html")
else:

    @app.get("/")
    def raiz() -> dict:
        return {"sistema": settings.app_name, "ambiente": settings.ambiente}
