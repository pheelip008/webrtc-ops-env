# Copyright (c) 2026. Licensed under BSD-3-Clause.
"""
WebRTC Ops Environment — Core Environment Logic

Implements the state machine that simulates a broken WebRTC infrastructure.
The agent issues operational commands (read_logs, modify_config, etc.)
and the environment returns observations with simulated CLI output,
system logs, and network metrics.

Three graded tasks:
  1. port_mismatch (Easy)   — WebSocket port mismatch between client and server
  2. sdp_codec_clash (Medium) — One-way audio due to codec negotiation failure
  3. congestion_degradation (Hard) — Multi-user session with degraded P2P path
"""

from __future__ import annotations

import copy
import json
import random
import textwrap
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from openenv.core.env_server.mcp_environment import MCPEnvironment
from openenv.core.env_server.types import Action, Observation, State

from fastmcp import FastMCP

from webrtc_ops_env.models import (
    WebRTCAction,
    WebRTCInternalState,
    WebRTCObservation,
)

# ─────────────────────────────────────────────────────────────────────
# Task definitions
# ─────────────────────────────────────────────────────────────────────

TASKS = ["port_mismatch", "sdp_codec_clash", "congestion_degradation"]
DEFAULT_TASK = "port_mismatch"
MAX_STEPS = 10


def _build_initial_state(task_name: str) -> WebRTCInternalState:
    """Create the initial 'broken' state for a given task."""

    if task_name == "port_mismatch":
        return WebRTCInternalState(
            task_name=task_name,
            signaling_status="port_mismatch",
            signaling_port=8080,
            client_expected_port=8081,
            active_sdp_offer="v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n",
            server_codecs=["Opus"],
            client_codecs=["Opus"],
            config={
                "port": 8080,
                "host": "0.0.0.0",
                "tls": False,
                "log_level": "info",
                "max_connections": 100,
            },
            peer_connections={},
            max_steps=MAX_STEPS,
        )

    elif task_name == "sdp_codec_clash":
        sdp = textwrap.dedent("""\
            v=0
            o=- 4867930 4867930 IN IP4 192.168.1.10
            s=WebRTC Session
            t=0 0
            m=audio 49170 RTP/AVP 0
            a=rtpmap:0 PCMU/8000
            a=sendrecv
        """).strip()
        return WebRTCInternalState(
            task_name=task_name,
            signaling_status="running",
            signaling_port=8080,
            client_expected_port=8080,
            active_sdp_offer=sdp,
            server_codecs=["Opus"],
            client_codecs=["PCMU"],
            config={
                "port": 8080,
                "host": "0.0.0.0",
                "tls": True,
                "log_level": "debug",
                "max_connections": 200,
                "allowed_codecs": ["Opus"],
            },
            peer_connections={
                "user_1": {
                    "packet_loss": 0.5,
                    "jitter": 3,
                    "relay_type": "host",
                    "bitrate": 2500,
                    "audio_bitrate": 0,
                    "status": "connected",
                },
            },
            max_steps=MAX_STEPS,
        )

    elif task_name == "congestion_degradation":
        return WebRTCInternalState(
            task_name=task_name,
            signaling_status="running",
            signaling_port=8080,
            client_expected_port=8080,
            active_sdp_offer="v=0\r\no=- 0 0 IN IP4 10.0.0.1\r\ns=Multi-User\r\nt=0 0\r\n",
            server_codecs=["Opus"],
            client_codecs=["Opus"],
            config={
                "port": 8080,
                "host": "0.0.0.0",
                "tls": True,
                "log_level": "warn",
                "max_connections": 500,
                "ice_servers": [
                    {"urls": "stun:stun.example.com:3478"},
                    {"urls": "turn:turn.example.com:3478", "username": "user", "credential": "pass"},
                ],
            },
            peer_connections={
                "user_1": {
                    "packet_loss": 1.2,
                    "jitter": 5,
                    "relay_type": "srflx",
                    "bitrate": 2500,
                    "audio_bitrate": 48,
                    "status": "connected",
                },
                "user_2": {
                    "packet_loss": 0.8,
                    "jitter": 3,
                    "relay_type": "srflx",
                    "bitrate": 2500,
                    "audio_bitrate": 48,
                    "status": "connected",
                },
                "user_3": {
                    "packet_loss": 35.0,
                    "jitter": 120,
                    "relay_type": "host",
                    "bitrate": 2500,
                    "audio_bitrate": 48,
                    "status": "degraded",
                },
                "user_4": {
                    "packet_loss": 2.0,
                    "jitter": 8,
                    "relay_type": "srflx",
                    "bitrate": 2500,
                    "audio_bitrate": 48,
                    "status": "connected",
                },
            },
            max_steps=MAX_STEPS,
        )

    else:
        raise ValueError(f"Unknown task: {task_name!r}. Choose from {TASKS}")


# ─────────────────────────────────────────────────────────────────────
# Log generators
# ─────────────────────────────────────────────────────────────────────

def _generate_logs(state: WebRTCInternalState) -> List[str]:
    """Generate simulated system logs based on the current state."""
    logs: List[str] = []

    if state.task_name == "port_mismatch":
        if state.signaling_status == "port_mismatch":
            logs.extend([
                f"[INFO] Signaling server started on port {state.signaling_port}",
                "[INFO] Waiting for WebSocket connections...",
                f"[WARN] Connection refused from client 192.168.1.50 on port {state.client_expected_port}. Is the WebSocket port correct?",
                f"[WARN] Connection refused from client 192.168.1.51 on port {state.client_expected_port}. Is the WebSocket port correct?",
                "[DEBUG] No active peer connections established",
                f"[INFO] Server config: port={state.signaling_port}, tls=false",
                f"[WARN] Client attempting connection on port {state.client_expected_port} but server listening on {state.signaling_port}",
                "[WARN] Repeated connection failures detected",
            ])
        elif state.signaling_status == "crashed":
            logs.extend([
                "[FATAL] Signaling server process terminated unexpectedly",
                "[ERROR] Service not responding on any port",
                "[INFO] Last known config: " + json.dumps(state.config),
            ])
        else:
            logs.extend([
                f"[INFO] Signaling server running on port {state.signaling_port}",
                "[INFO] All systems nominal",
                "[INFO] WebSocket connections active",
            ])

    elif state.task_name == "sdp_codec_clash":
        if state.peer_connections.get("user_1", {}).get("audio_bitrate", 0) == 0:
            logs.extend([
                "[INFO] Signaling server running on port 8080",
                "[INFO] user_1 connected via WebSocket",
                "[INFO] SDP offer received from user_1",
                "[ERROR] SDP Negotiation failed: No matching payload type for audio",
                "[ERROR] Client requests PCMU (payload type 0) but server only supports Opus (payload type 111)",
                "[WARN] Audio track not established for user_1 — one-way audio bug detected",
                "[INFO] Video track active for user_1: VP8 @ 2500 kbps",
                "[DEBUG] SDP offer payload:\n" + state.active_sdp_offer,
                "[WARN] Check allowed_codecs in configuration",
            ])
        else:
            logs.extend([
                "[INFO] Signaling server running on port 8080",
                "[INFO] SDP negotiation successful — codec: Opus",
                f"[INFO] Audio bitrate: {state.peer_connections['user_1']['audio_bitrate']} kbps",
                "[INFO] All media tracks active",
            ])

    elif state.task_name == "congestion_degradation":
        user3 = state.peer_connections.get("user_3", {})
        pkt_loss = user3.get("packet_loss", 35.0)
        relay = user3.get("relay_type", "host")
        bitrate = user3.get("bitrate", 2500)

        logs.extend([
            "[INFO] Multi-user session active: 4 participants",
            "[INFO] user_1: stable (srflx), packet_loss=1.2%",
            "[INFO] user_2: stable (srflx), packet_loss=0.8%",
            f"[WARN] user_3: {'degraded' if pkt_loss > 10 else 'stable'} ({relay}), packet_loss={pkt_loss}%",
            "[INFO] user_4: stable (srflx), packet_loss=2.0%",
        ])

        if pkt_loss > 10:
            logs.extend([
                f"[WARN] NACK bursts detected for user_3 — packet_loss={pkt_loss}%",
                f"[WARN] user_3 is on a direct {relay} ICE candidate (P2P)",
                "[WARN] Consider routing user_3 through a TURN relay server",
                f"[INFO] user_3 current video bitrate: {bitrate} kbps",
            ])
        elif relay == "relay":
            logs.append("[INFO] user_3 routed through TURN relay — connection stabilized")
            if bitrate <= 500:
                logs.append(f"[INFO] user_3 bitrate adjusted to {bitrate} kbps — congestion mitigated")

    return logs[-10:]  # Keep last 10 lines


def _generate_metrics(state: WebRTCInternalState) -> Dict[str, Any]:
    """Generate network metrics from the current state."""
    metrics: Dict[str, Any] = {}
    for user_id, conn in state.peer_connections.items():
        metrics[user_id] = {
            "packet_loss_pct": conn.get("packet_loss", 0),
            "jitter_ms": conn.get("jitter", 0),
            "video_bitrate_kbps": conn.get("bitrate", 0),
            "audio_bitrate_kbps": conn.get("audio_bitrate", 48),
            "relay_type": conn.get("relay_type", "host"),
            "status": conn.get("status", "unknown"),
        }
    return metrics


# ─────────────────────────────────────────────────────────────────────
# Graders
# ─────────────────────────────────────────────────────────────────────

def _grade_port_mismatch(state: WebRTCInternalState) -> float:
    """Score: 1.0 if port is fixed AND service restarted."""
    if state.config.get("port") == state.client_expected_port and state.service_restarted_since_fix:
        return 1.0
    return 0.0


def _grade_sdp_codec_clash(state: WebRTCInternalState) -> float:
    """Score: 1.0 if Opus is in allowed_codecs and audio bitrate recovered."""
    codecs = state.config.get("allowed_codecs", [])
    user1 = state.peer_connections.get("user_1", {})
    if "PCMU" in codecs or "Opus" in codecs:
        if user1.get("audio_bitrate", 0) >= 48:
            return 1.0
    return 0.0


def _grade_congestion_degradation(state: WebRTCInternalState) -> float:
    """Partial scoring: +0.5 for TURN relay, +0.5 for bitrate adjustment."""
    score = 0.0
    user3 = state.peer_connections.get("user_3", {})

    if user3.get("relay_type") in ("relay", "TURN"):
        score += 0.5

    if user3.get("bitrate", 2500) <= 500:
        score += 0.5

    return score


GRADERS = {
    "port_mismatch": _grade_port_mismatch,
    "sdp_codec_clash": _grade_sdp_codec_clash,
    "congestion_degradation": _grade_congestion_degradation,
}


# ─────────────────────────────────────────────────────────────────────
# Environment
# ─────────────────────────────────────────────────────────────────────

class WebRTCOpsEnvironment(MCPEnvironment):
    """Simulated WebRTC Operations Environment.

    An AI agent interacts with a fake WebRTC infrastructure through
    operational commands (read_logs, restart_signaling, modify_config,
    force_ice_relay, adjust_bitrate) and must diagnose and fix issues.

    The environment is a pure state machine — no real servers are
    started. This keeps it lightweight enough for 2 vCPU / 8GB RAM
    containers with a 20-minute inference limit.
    """

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        # ── FastMCP tools ──
        mcp = FastMCP("webrtc_ops_env")

        @mcp.tool
        def read_logs(target: str = "system") -> str:
            """Read system logs or a configuration file.

            Args:
                target: 'system' for server logs, or a config filename like 'signaling.yaml'

            Returns:
                The requested log or config content as a string.
            """
            action = WebRTCAction(command="read_logs", target=target)
            obs = self._execute_action(action)
            return obs.terminal_output

        @mcp.tool
        def restart_signaling() -> str:
            """Restart the signaling server service.

            Returns:
                Terminal output confirming restart status.
            """
            action = WebRTCAction(command="restart_signaling")
            obs = self._execute_action(action)
            return obs.terminal_output

        @mcp.tool
        def modify_config(target: str, key: str, value: str) -> str:
            """Modify a configuration parameter.

            Args:
                target: Config file to modify (e.g. 'signaling.yaml')
                key: Configuration key to change (e.g. 'port', 'allowed_codecs')
                value: New value (strings, numbers, or JSON arrays)

            Returns:
                Terminal output confirming the modification.
            """
            action = WebRTCAction(command="modify_config", target=target, key=key, value=value)
            obs = self._execute_action(action)
            return obs.terminal_output

        @mcp.tool
        def force_ice_relay(target: str, value: str = "TURN") -> str:
            """Force a user's ICE candidate type to route through a specific relay.

            Args:
                target: User ID (e.g. 'user_3')
                value: Relay type — typically 'TURN' for relay server routing

            Returns:
                Terminal output confirming the relay change.
            """
            action = WebRTCAction(command="force_ice_relay", target=target, value=value)
            obs = self._execute_action(action)
            return obs.terminal_output

        @mcp.tool
        def adjust_bitrate(target: str, value: str) -> str:
            """Adjust the video bitrate cap for a specific user.

            Args:
                target: User ID (e.g. 'user_3')
                value: New bitrate in kbps (e.g. '250', '500')

            Returns:
                Terminal output confirming the bitrate adjustment.
            """
            action = WebRTCAction(command="adjust_bitrate", target=target, value=value)
            obs = self._execute_action(action)
            return obs.terminal_output

        super().__init__(mcp)
        self._state_obj = State(episode_id=str(uuid4()), step_count=0)
        self._internal: WebRTCInternalState = _build_initial_state(DEFAULT_TASK)

    # ── OpenEnv interface ──────────────────────────────────────────

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        task_name: Optional[str] = None,
        **kwargs: Any,
    ) -> Observation:
        """Reset the environment to a new broken state.

        Args:
            seed: Optional random seed (for reproducibility)
            episode_id: Optional custom episode ID
            task_name: One of 'port_mismatch', 'sdp_codec_clash', 'congestion_degradation'
        """
        if seed is not None:
            random.seed(seed)

        task = task_name or kwargs.get("task", DEFAULT_TASK)
        self._internal = _build_initial_state(task)
        self._state_obj = State(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
        )

        logs = _generate_logs(self._internal)
        metrics = _generate_metrics(self._internal)

        return Observation(
            done=False,
            reward=0.0,
            metadata={
                "terminal_output": f"Environment reset. Task: {task}. Use read_logs to begin diagnosis.",
                "system_logs": logs,
                "network_metrics": metrics,
                "task_name": task,
            },
        )

    def step(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """Execute an agent action and return the resulting observation."""
        self._state_obj.step_count += 1

        # If it's a WebRTCAction, handle directly
        if isinstance(action, WebRTCAction):
            obs = self._execute_action(action)
            # Convert to base Observation for the HTTP/WS layer
            return Observation(
                done=obs.done,
                reward=obs.reward,
                metadata={
                    "terminal_output": obs.terminal_output,
                    "system_logs": obs.system_logs,
                    "network_metrics": obs.network_metrics,
                },
            )

        # Delegate MCP actions to base class
        return super().step(action, timeout_s=timeout_s, **kwargs)

    async def step_async(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """Async step for the WebSocket handler."""
        self._state_obj.step_count += 1

        if isinstance(action, WebRTCAction):
            obs = self._execute_action(action)
            return Observation(
                done=obs.done,
                reward=obs.reward,
                metadata={
                    "terminal_output": obs.terminal_output,
                    "system_logs": obs.system_logs,
                    "network_metrics": obs.network_metrics,
                },
            )

        return await super().step_async(action, timeout_s=timeout_s, **kwargs)

    def _step_impl(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """Handle non-MCP, non-WebRTC actions."""
        return Observation(
            done=False,
            reward=0.0,
            metadata={
                "error": f"Unknown action type: {type(action).__name__}. "
                "Use WebRTCAction or MCP tool calls.",
            },
        )

    @property
    def state(self) -> State:
        return self._state_obj

    # ── Core state-machine logic ───────────────────────────────────

    def _execute_action(self, action: WebRTCAction) -> WebRTCObservation:
        """Process an action against the internal state and return an observation."""
        s = self._internal

        if s.is_done:
            return WebRTCObservation(
                done=True,
                reward=0.0,
                terminal_output="Episode is already finished.",
                system_logs=_generate_logs(s),
                network_metrics=_generate_metrics(s),
            )

        s.steps_taken += 1
        s.actions_taken.append(f"{action.command}({action.target or ''}, {action.key or ''}, {action.value or ''})")

        reward = 0.0
        terminal_output = ""

        try:
            if action.command == "read_logs":
                terminal_output, reward = self._handle_read_logs(action)
            elif action.command == "restart_signaling":
                terminal_output, reward = self._handle_restart_signaling(action)
            elif action.command == "modify_config":
                terminal_output, reward = self._handle_modify_config(action)
            elif action.command == "force_ice_relay":
                terminal_output, reward = self._handle_force_ice_relay(action)
            elif action.command == "adjust_bitrate":
                terminal_output, reward = self._handle_adjust_bitrate(action)
            else:
                terminal_output = f"Unknown command: {action.command}"
                reward = -0.1
        except Exception as e:
            terminal_output = f"Error executing {action.command}: {e}"
            reward = -0.1

        # Valid syntactic action bonus (if no error)
        if reward >= 0:
            reward += 0.1

        # Compute task score
        grader = GRADERS.get(s.task_name)
        if grader:
            s.task_score = grader(s)

        # Check if done
        if s.task_score >= 1.0 or s.steps_taken >= s.max_steps:
            s.is_done = True

        s.cumulative_reward += reward
        s.cumulative_reward = min(s.cumulative_reward, 1.0)

        logs = _generate_logs(s)
        metrics = _generate_metrics(s)

        return WebRTCObservation(
            done=s.is_done,
            reward=round(reward, 2),
            terminal_output=terminal_output,
            system_logs=logs,
            network_metrics=metrics,
        )

    # ── Command handlers ───────────────────────────────────────────

    def _handle_read_logs(self, action: WebRTCAction) -> tuple[str, float]:
        """Handle the read_logs command."""
        s = self._internal
        target = (action.target or "system").strip().lower()

        if target in ("system", "logs", "server"):
            logs = _generate_logs(s)
            output = "=== System Logs ===\n" + "\n".join(logs)
            return output, 0.0

        elif target in ("signaling.yaml", "signaling", "config"):
            config_str = json.dumps(s.config, indent=2)
            output = f"=== signaling.yaml ===\n{config_str}"
            return output, 0.0

        elif target in ("sdp", "sdp_offer", "sdp.txt"):
            output = f"=== Active SDP Offer ===\n{s.active_sdp_offer}"
            return output, 0.0

        elif target in ("metrics", "network"):
            metrics = _generate_metrics(s)
            output = "=== Network Metrics ===\n" + json.dumps(metrics, indent=2)
            return output, 0.0

        else:
            return f"File not found: {target}", -0.05

    def _handle_restart_signaling(self, action: WebRTCAction) -> tuple[str, float]:
        """Handle the restart_signaling command."""
        s = self._internal
        reward = 0.0

        if s.signaling_status == "crashed":
            return "ERROR: Cannot restart — service binary is corrupted. Reinstall required.", -0.2

        # If config was changed, mark the restart
        if s.config_changed:
            s.service_restarted_since_fix = True

        # Update signaling port from config
        new_port = s.config.get("port", s.signaling_port)
        s.signaling_port = new_port

        # Check if port mismatch is resolved
        if s.signaling_port == s.client_expected_port:
            s.signaling_status = "running"
            reward = 0.2
        else:
            s.signaling_status = "port_mismatch" if s.signaling_port != s.client_expected_port else "running"

        output = (
            f"Signaling service restarted successfully.\n"
            f"Listening on port {s.signaling_port}.\n"
            f"Status: {s.signaling_status}"
        )
        return output, reward

    def _handle_modify_config(self, action: WebRTCAction) -> tuple[str, float]:
        """Handle the modify_config command."""
        s = self._internal
        target = (action.target or "").strip().lower()
        key = action.key
        value = action.value

        if not key or value is None:
            return "ERROR: modify_config requires 'key' and 'value' parameters.", -0.1

        if target not in ("signaling.yaml", "signaling", "config", ""):
            return f"ERROR: Unknown config file: {target}", -0.1

        # Parse value
        parsed_value: Any = value
        try:
            parsed_value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # Try int/float
            try:
                parsed_value = int(value)
            except ValueError:
                try:
                    parsed_value = float(value)
                except ValueError:
                    parsed_value = value  # Keep as string

        old_value = s.config.get(key, "<not set>")
        s.config[key] = parsed_value
        s.config_changed = True

        reward = 0.0

        # Task-specific reward for correct modifications
        if s.task_name == "port_mismatch" and key == "port":
            if parsed_value == s.client_expected_port:
                reward = 0.3  # Correct port fix

        elif s.task_name == "sdp_codec_clash" and key == "allowed_codecs":
            if isinstance(parsed_value, list):
                if "PCMU" in parsed_value or "Opus" in parsed_value:
                    # Update the server codecs and simulate negotiation success
                    s.server_codecs = parsed_value
                    # If both client and server now share a codec, fix the audio
                    shared = set(s.server_codecs) & set(s.client_codecs)
                    if shared or "PCMU" in parsed_value:
                        user1 = s.peer_connections.get("user_1", {})
                        user1["audio_bitrate"] = 48
                        user1["status"] = "connected"
                        s.peer_connections["user_1"] = user1
                        reward = 0.4
            elif isinstance(parsed_value, str):
                # Agent might pass a single codec as a string
                if parsed_value in ("PCMU", "Opus"):
                    s.server_codecs.append(parsed_value)
                    s.config["allowed_codecs"] = s.server_codecs
                    if parsed_value in s.client_codecs or parsed_value == "PCMU":
                        user1 = s.peer_connections.get("user_1", {})
                        user1["audio_bitrate"] = 48
                        user1["status"] = "connected"
                        s.peer_connections["user_1"] = user1
                        reward = 0.4

        output = (
            f"Configuration updated: {key} = {json.dumps(parsed_value)}\n"
            f"Previous value: {old_value}\n"
            f"Note: Restart the signaling service for changes to take effect."
        )
        return output, reward

    def _handle_force_ice_relay(self, action: WebRTCAction) -> tuple[str, float]:
        """Handle the force_ice_relay command."""
        s = self._internal
        target = action.target
        relay_type = (action.value or "TURN").strip().upper()

        if not target:
            return "ERROR: force_ice_relay requires a 'target' user ID (e.g. 'user_3').", -0.1

        if target not in s.peer_connections:
            return f"ERROR: User '{target}' not found in active peer connections.", -0.1

        user = s.peer_connections[target]
        old_relay = user.get("relay_type", "host")

        if relay_type in ("TURN", "RELAY"):
            user["relay_type"] = "relay"
            user["status"] = "connected"

            # Routing through TURN server reduces packet loss significantly
            if user.get("packet_loss", 0) > 10:
                user["packet_loss"] = round(random.uniform(1.0, 5.0), 1)
                user["jitter"] = random.randint(5, 15)

            s.peer_connections[target] = user
            output = (
                f"ICE relay forced for {target}: {old_relay} → relay (TURN)\n"
                f"Packet loss: {user['packet_loss']}%, Jitter: {user['jitter']}ms\n"
                f"Connection stabilized via TURN server."
            )
            return output, 0.3

        else:
            return f"ERROR: Unsupported relay type '{relay_type}'. Use 'TURN'.", -0.1

    def _handle_adjust_bitrate(self, action: WebRTCAction) -> tuple[str, float]:
        """Handle the adjust_bitrate command."""
        s = self._internal
        target = action.target
        value = action.value

        if not target:
            return "ERROR: adjust_bitrate requires a 'target' user ID (e.g. 'user_3').", -0.1

        if target not in s.peer_connections:
            return f"ERROR: User '{target}' not found in active peer connections.", -0.1

        if not value:
            return "ERROR: adjust_bitrate requires a 'value' (bitrate in kbps).", -0.1

        try:
            new_bitrate = int(value)
        except ValueError:
            return f"ERROR: Invalid bitrate value: {value!r}. Must be an integer (kbps).", -0.1

        if new_bitrate < 50 or new_bitrate > 10000:
            return f"ERROR: Bitrate {new_bitrate} kbps out of range (50–10000).", -0.1

        user = s.peer_connections[target]
        old_bitrate = user.get("bitrate", 2500)
        user["bitrate"] = new_bitrate
        s.peer_connections[target] = user

        reward = 0.0
        if s.task_name == "congestion_degradation" and target == "user_3":
            if new_bitrate <= 500:
                reward = 0.3  # Appropriate reduction for congested user

        output = (
            f"Video bitrate for {target} adjusted: {old_bitrate} → {new_bitrate} kbps\n"
            f"Current connection: packet_loss={user['packet_loss']}%, relay={user['relay_type']}"
        )
        return output, reward
