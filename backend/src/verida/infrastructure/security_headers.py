"""Security headers middleware for VERIDA.

Adds the following response headers to every request:
- Strict-Transport-Security (HSTS)
- X-Content-Type-Options
- X-Frame-Options
- Referrer-Policy
- Content-Security-Policy (no unsafe-inline, no unsafe-eval)
- Permissions-Policy

These headers harden the application against common web vulnerabilities:
clickjacking, MIME sniffing, cross-site scripting, and information leakage.

Design:
- Pure middleware — no business logic
- CSP is strict: no 'unsafe-inline', no 'unsafe-eval'
- For local development, HSTS max-age is set to 0 to avoid pinning localhost
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


# Content Security Policy — strict, no unsafe-inline
# Adjust connect-src if you add WebSocket or third-party API endpoints.
_CSP_DIRECTIVES = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data: blob:",
        "font-src 'self'",
        "connect-src 'self'",
        "media-src 'self' blob:",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "upgrade-insecure-requests",
    ]
)

_PERMISSIONS_POLICY = ", ".join(
    [
        "camera=(self)",       # needed for daily moment capture
        "microphone=(self)",   # needed for video capture
        "geolocation=()",      # explicitly disabled
        "payment=()",          # no payment in MVP
        "usb=()",
        "interest-cohort=()",  # FLoC opt-out
    ]
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Starlette/FastAPI middleware that adds security headers to all responses.

    Usage::

        app.add_middleware(SecurityHeadersMiddleware, environment="production")

    Parameters
    ----------
    app:
        The ASGI application to wrap.
    environment:
        If ``"production"``, HSTS max-age is 1 year with includeSubDomains.
        Otherwise, HSTS max-age is 0 to avoid pinning development hosts.
    """

    def __init__(self, app: ASGIApp, environment: str = "development") -> None:
        super().__init__(app)
        self._environment = environment

        if environment == "production":
            self._hsts = "max-age=31536000; includeSubDomains; preload"
        else:
            self._hsts = "max-age=0"

    async def dispatch(self, request: Request, call_next: object) -> Response:
        response: Response = await call_next(request)  # type: ignore[arg-type]

        response.headers["Strict-Transport-Security"] = self._hsts
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = _CSP_DIRECTIVES
        response.headers["Permissions-Policy"] = _PERMISSIONS_POLICY
        response.headers["X-XSS-Protection"] = "0"  # Modern browsers — CSP is better

        # Remove headers that leak server information
        response.headers.update({"X-Served-By": ""})
        if "Server" in response.headers:
            del response.headers["Server"]
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]

        return response
