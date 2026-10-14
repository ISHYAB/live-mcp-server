
import hashlib
from contextlib import asynccontextmanager
from contextvars import ContextVar

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount

EMAIL = "23f3003296@ds.study.iitm.ac.in"

# Isolated per HTTP request, so concurrent calls don't share challenges.
current_challenge = ContextVar("current_challenge", default=None)


class HeaderCapture:
    """Capture the HTTP headers for the current MCP request."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.lower(): value
            for key, value in scope.get("headers", [])
        }
        challenge = headers.get(b"x-exam-challenge", b"").decode("ascii")

        token = current_challenge.set(challenge)
        try:
            await self.app(scope, receive, send)
        finally:
            current_challenge.reset(token)


mcp = FastMCP(
    "Live Exam MCP Server",
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def solve_challenge() -> str:
    """Solve the current challenge supplied in the HTTP request headers."""
    challenge = current_challenge.get()

    if not challenge:
        raise ValueError("Missing X-Exam-Challenge header")

    value = f"{challenge}:{EMAIL}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


@asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield


app = Starlette(
    routes=[
        Mount("/", app=HeaderCapture(mcp.streamable_http_app()))
    ],
    lifespan=lifespan,
)
