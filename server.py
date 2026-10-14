
import hashlib
from contextvars import ContextVar

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

EMAIL = "23f3003296@ds.study.iitm.ac.in"
HOST = "live-mcp-server-9hz5.onrender.com"

current_challenge = ContextVar("current_challenge", default=None)

mcp = FastMCP(
    "Live Exam MCP Server",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


@mcp.tool()
def solve_challenge() -> str:
    """Compute the response from the current HTTP challenge header."""
    challenge = current_challenge.get()

    if not challenge:
        raise ValueError("Missing X-Exam-Challenge header")

    payload = f"{challenge}:{EMAIL}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class HeaderCapture:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        challenge = headers.get(
            b"x-exam-challenge", b""
        ).decode("ascii")

        token = current_challenge.set(challenge)
        try:
            await self.app(scope, receive, send)
        finally:
            current_challenge.reset(token)


app = HeaderCapture(mcp.streamable_http_app())
