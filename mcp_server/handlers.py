import logging
from fastapi import Request, Response
from mcp.server.sse import SseServerTransport
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions
from starlette.routing import Route

from mcp_server.server import mcp_server
from core.system import SDTBSystem

def get_system():
    return SDTBSystem()

logger = logging.getLogger("sdtb_mcp")

# Define the SSE transport
sse = SseServerTransport("/mcp/messages")

# To avoid "Unexpected ASGI message" and "NoneType is not callable" errors,
# we use a NoOpResponse that tells Starlette the response is already handled.
class NoOpResponse(Response):
    async def __call__(self, scope, receive, send):
        return

async def handle_sse(request: Request):
    """Handle the SSE connection for MCP."""
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="sdtb-commander",
                server_version=get_system().version,
                capabilities=mcp_server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
    return NoOpResponse()

async def handle_messages(request: Request):
    """Handle incoming MCP messages over the SSE transport."""
    await sse.handle_post_message(request.scope, request.receive, request._send)
    return NoOpResponse()

mcp_routes = [
    Route("/mcp/sse", endpoint=handle_sse, methods=["GET"]),
    Route("/mcp/messages", endpoint=handle_messages, methods=["POST"]),
]
