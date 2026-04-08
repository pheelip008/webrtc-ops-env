# Copyright (c) 2026. Licensed under BSD-3-Clause.
"""
WebRTC Ops Environment — Simulated WebRTC Infrastructure Diagnostics

An OpenEnv environment where AI agents diagnose and fix simulated
WebRTC infrastructure issues using operational commands.

Available MCP tools:
- read_logs(target): Read system logs or config files
- restart_signaling(): Restart the signaling service
- modify_config(target, key, value): Modify configuration parameters
- force_ice_relay(target, value): Force ICE relay routing for a user
- adjust_bitrate(target, value): Adjust video bitrate for a user

Example:
    >>> from webrtc_ops_env import WebRTCOpsEnv
    >>>
    >>> with WebRTCOpsEnv(base_url="http://localhost:8000") as env:
    ...     env.reset()
    ...     tools = env.list_tools()
    ...     result = env.call_tool("read_logs", target="system")
    ...     print(result)
"""

from openenv.core.env_server.mcp_types import CallToolAction, ListToolsAction

from .client import WebRTCOpsEnv
from .models import WebRTCAction, WebRTCObservation

__all__ = [
    "WebRTCOpsEnv",
    "WebRTCAction",
    "WebRTCObservation",
    "CallToolAction",
    "ListToolsAction",
]
