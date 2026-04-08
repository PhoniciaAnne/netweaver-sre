# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the Netweaver Sre Environment.

This module creates an HTTP server that exposes the NetweaverSreEnvironment
over HTTP and WebSocket endpoints, compatible with EnvClient.

Endpoints:
    - POST /reset: Reset the environment
    - POST /step: Execute an action
    - GET /state: Get current environment state
    - GET /schema: Get action/observation schemas
    - WS /ws: WebSocket endpoint for persistent sessions

Usage:
    # Development (with auto-reload):
    uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

    # Production:
    uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4

    # Or run directly:
    python -m server.app
"""

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:  # pragma: no cover
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
    ) from e

try:
    from ..models import NetweaverSreAction, NetweaverSreObservation
    from .netweaver_sre_environment import NetweaverSreEnvironment, set_task_level
except (ModuleNotFoundError, ImportError):
    from models import NetweaverSreAction, NetweaverSreObservation
    from server.netweaver_sre_environment import NetweaverSreEnvironment, set_task_level


# Create the app with web interface and README integration
app = create_app(
    NetweaverSreEnvironment,
    NetweaverSreAction,
    NetweaverSreObservation,
    env_name="netweaver_sre",
    max_concurrent_envs=1,  # increase this number to allow more concurrent WebSocket sessions
)

# ----- Custom routes -----
from fastapi import Request

from fastapi.responses import FileResponse
import os

@app.get("/")
async def root():
    html_path = os.path.join(os.path.dirname(__file__), "playground.html")
    return FileResponse(html_path)

@app.get("/pro")
async def pro_ui():
    """Premium enhanced UI with analytics, history, and leaderboard."""
    html_path = os.path.join(os.path.dirname(__file__), "playground_enhanced.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    else:
        # Fallback to standard UI
        html_path = os.path.join(os.path.dirname(__file__), "playground.html")
        return FileResponse(html_path)

@app.post("/set_level")
async def configure_task_level(request: Request):
    """Pin the task difficulty for the next /reset call."""
    body = await request.json()
    level = body.get("task_level", "").lower()
    if level not in ("easy", "medium", "hard", ""):
        return {"error": f"Invalid level '{level}'. Choose: easy, medium, hard"}
    set_task_level(level)
    return {"success": True, "task_level": level or "random"}


def main():
    """
    Entry point for the server.
    """
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7860) # Use 7860 for HF compatibility
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
