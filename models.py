# Copyright (c) 2026. Licensed under BSD-3-Clause.
"""
WebRTC Ops Environment — Pydantic Models

Defines the typed Action, Observation, and internal State models
for the simulated WebRTC operations environment.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from openenv.core.env_server.types import Action, Observation, State


# ─────────────────────────────────────────────────────────────────────
# Action: What the agent sends
# ─────────────────────────────────────────────────────────────────────

class WebRTCAction(Action):
    """An operational command issued by the agent to the WebRTC system.

    The agent selects one of five commands and optionally specifies
    a target resource, configuration key, and new value.
    """

    command: Literal[
        "read_logs",
        "restart_signaling",
        "modify_config",
        "force_ice_relay",
        "adjust_bitrate",
    ] = Field(description="The operational command to execute.")

    target: Optional[str] = Field(
        default=None,
        description=(
            "Target resource for the command. "
            "E.g. 'signaling.yaml' for config reads, 'user_3' for per-user actions."
        ),
    )

    key: Optional[str] = Field(
        default=None,
        description="Configuration key to read or modify (used with modify_config).",
    )

    value: Optional[str] = Field(
        default=None,
        description="New value for the configuration key or action parameter.",
    )


# ─────────────────────────────────────────────────────────────────────
# Observation: What the agent sees after every step
# ─────────────────────────────────────────────────────────────────────

class WebRTCObservation(Observation):
    """The agent-visible observation returned after each step.

    Contains simulated terminal output, recent system logs,
    and current network metrics for all active connections.
    """

    terminal_output: str = Field(
        default="",
        description="Simulated CLI output from the last command.",
    )

    system_logs: List[str] = Field(
        default_factory=list,
        description="The last N lines of simulated server logs.",
    )

    network_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Current network metrics for active connections. "
            "Keys are user IDs; values contain packet_loss, jitter, bitrate, etc."
        ),
    )


# ─────────────────────────────────────────────────────────────────────
# Internal State: Hidden from the agent — drives the simulation
# ─────────────────────────────────────────────────────────────────────

class WebRTCInternalState(BaseModel):
    """Internal simulation state that the agent never sees directly.

    This is the 'fake network' — every field represents some aspect
    of the simulated WebRTC infrastructure that the agent must diagnose
    and repair through its actions.
    """

    # ── Task identity ──
    task_name: str = Field(description="Active task identifier.")

    # ── Signaling server ──
    signaling_status: Literal["running", "crashed", "port_mismatch"] = Field(
        default="running",
        description="Current health of the signaling service.",
    )
    signaling_port: int = Field(
        default=8080,
        description="Port the signaling server is actually listening on.",
    )
    client_expected_port: int = Field(
        default=8080,
        description="Port the client is trying to connect to.",
    )

    # ── SDP / Codec ──
    active_sdp_offer: str = Field(
        default="",
        description="Current SDP payload string.",
    )
    server_codecs: List[str] = Field(
        default_factory=lambda: ["Opus"],
        description="Audio codecs the server supports.",
    )
    client_codecs: List[str] = Field(
        default_factory=lambda: ["Opus"],
        description="Audio codecs the client is requesting.",
    )

    # ── Config file simulation ──
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Contents of the simulated signaling.yaml.",
    )

    # ── Peer connections ──
    peer_connections: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description=(
            "Per-user connection state. "
            "Each entry: {packet_loss, jitter, relay_type, bitrate, audio_bitrate}."
        ),
    )

    # ── Episode bookkeeping ──
    service_restarted_since_fix: bool = Field(
        default=False,
        description="Whether the signaling service was restarted after a config change.",
    )
    config_changed: bool = Field(
        default=False,
        description="Whether any configuration was modified this episode.",
    )
    actions_taken: List[str] = Field(
        default_factory=list,
        description="History of command strings executed this episode.",
    )
    cumulative_reward: float = Field(
        default=0.0,
        description="Sum of rewards earned so far.",
    )
    steps_taken: int = Field(
        default=0,
        description="Number of steps executed.",
    )
    max_steps: int = Field(
        default=10,
        description="Maximum steps before episode auto-terminates.",
    )
    is_done: bool = Field(
        default=False,
        description="Whether the episode is finished.",
    )
    task_score: float = Field(
        default=0.0,
        description="Grader score for the current task (0.0–1.0).",
    )
