# Copyright (c) 2026. Licensed under BSD-3-Clause.
"""
WebRTC Ops Environment Client.

Provides the client for connecting to a WebRTC Ops Environment server.
Extends MCPToolClient for tool-calling style interactions.

Example:
    >>> with WebRTCOpsEnv(base_url="http://localhost:8000") as env:
    ...     env.reset()
    ...     tools = env.list_tools()
    ...     result = env.call_tool("read_logs", target="system")
    ...     print(result)

Example with Docker:
    >>> env = WebRTCOpsEnv.from_docker_image("webrtc-ops-env:latest")
    >>> try:
    ...     env.reset()
    ...     tools = env.list_tools()
    ...     result = env.call_tool("read_logs", target="signaling.yaml")
    ... finally:
    ...     env.close()

Example with HuggingFace Space:
    >>> env = WebRTCOpsEnv.from_env("pheelip0030/webrtc-ops-env")
    >>> try:
    ...     env.reset()
    ...     result = env.call_tool("modify_config", target="signaling.yaml", key="port", value="8081")
    ... finally:
    ...     env.close()
"""

from openenv.core.mcp_client import MCPToolClient


class WebRTCOpsEnv(MCPToolClient):
    """Client for the WebRTC Ops Environment.

    Inherits all functionality from MCPToolClient:
    - list_tools(): Discover available operational tools
    - call_tool(name, **kwargs): Call an operational tool
    - reset(**kwargs): Reset the environment to a new broken state
    - step(action): Execute a raw action (for advanced use)
    """

    pass  # MCPToolClient provides all needed functionality
