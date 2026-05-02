from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await sdtb_system.startup()
    yield
    # Shutdown
    await sdtb_system.shutdown()

app = FastAPI(
    title="Software Defined Test Bench (SDTB)",
    description="A hardware-agnostic REST API and UI for controlling test hardware.",
    version="0.1.0",
    lifespan=lifespan
)

from routers import system, device, channel, test, ui, mcp, flash

# Access the singleton system instance via call
sdtb_system = system.get_system()

app.include_router(system.router)
app.include_router(device.router)
app.include_router(channel.router)
app.include_router(test.router)
app.include_router(flash.router)
app.include_router(ui.router)

# Special handling for MCP routes to avoid ASGI response conflicts
for route in mcp.mcp_routes:
    app.router.routes.append(route)

# Mount the UI static files
app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")

@app.get("/")
async def root():
    return {"message": "Welcome to SDTB API. Visit /docs for documentation."}

@app.get("/ping")
async def ping():
    return {"message": "pong"}

if __name__ == "__main__":
    import os
    # Ensure uvicorn uses the right module path if run directly
    config = sdtb_system.system_config.server
    uvicorn.run(app, host=config.host, port=config.port)
