from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Headers de segurança padrão — seção 13 do plano (Infraestrutura de segurança)."""

    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        # 'self' liberado para script/style/img/font/connect: o mesmo serviço
        # serve a API e o build estático da SPA na mesma origem (seção 2 do
        # plano) — "default-src 'none'" bloqueava o próprio JS/CSS do
        # frontend, resultando em tela em branco.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'"
        )
        response.headers["Cache-Control"] = "no-store"
        if self._settings.is_producao:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response
