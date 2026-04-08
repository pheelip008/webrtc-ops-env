# Copyright (c) 2026. Licensed under BSD-3-Clause.
"""
FastAPI application for the WebRTC Ops Environment.

Exposes the environment over HTTP and WebSocket endpoints.

Usage:
    uvicorn server.app:app --reload --host 0.0.0.0 --port 8000
"""

# Support both in-repo and standalone imports
try:
    from openenv.core.env_server.http_server import create_app
    from openenv.core.env_server.mcp_types import CallToolAction, CallToolObservation
    from .webrtc_environment import WebRTCOpsEnvironment
except ImportError:
    from openenv.core.env_server.http_server import create_app
    from openenv.core.env_server.mcp_types import CallToolAction, CallToolObservation
    from server.webrtc_environment import WebRTCOpsEnvironment

# Create the app — pass the class (factory) for WebSocket session support
app = create_app(
    WebRTCOpsEnvironment, CallToolAction, CallToolObservation, env_name="webrtc_ops_env"
)


def main():
    """Entry point for direct execution."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
