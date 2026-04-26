from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    sdtb_system.startup()
    yield
    # Shutdown
    await sdtb_system.shutdown()

app = FastAPI(
    title="Software Defined Test Bench (SDTB)",
    description="A hardware-agnostic REST API and UI for controlling test hardware.",
    version="0.1.0",
    lifespan=lifespan
)

from routers import system, device, channel, test, ui, mcp

# Access the singleton system instance
sdtb_system = system.system

app.include_router(system.router)
app.include_router(device.router)
app.include_router(channel.router)
app.include_router(test.router)
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
