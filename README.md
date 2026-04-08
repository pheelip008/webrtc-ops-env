# WebRTC Ops Environment 🌐🔧

A simulated WebRTC infrastructure diagnostics environment built on the [OpenEnv](https://github.com/meta-pytorch/OpenEnv) framework. AI agents diagnose and fix realistic WebRTC issues — port mismatches, codec negotiation failures, and network congestion — using operational CLI commands.

**No real WebRTC servers are started.** The environment is a pure Python state machine that simulates broken infrastructure, making it lightweight enough to run within 2 vCPUs and 8GB RAM.

## 🎯 Real-World Motivation

WebRTC infrastructure operations is a genuine task performed by DevOps and network engineers daily:
- Diagnosing signaling server misconfigurations
- Debugging one-way audio caused by SDP codec mismatches
- Mitigating congestion for users on degraded network paths

This environment models these exact scenarios, providing a benchmark for evaluating how well AI agents can perform infrastructure troubleshooting.

## 🛠️ Action Space

The agent issues operational commands via a unified `WebRTCAction` model:

| Command | Target | Key | Value | Description |
|---------|--------|-----|-------|-------------|
| `read_logs` | `system`, `signaling.yaml`, `sdp`, `metrics` | — | — | Read logs or config files |
| `restart_signaling` | — | — | — | Restart the signaling service |
| `modify_config` | `signaling.yaml` | Config key | New value | Modify a config parameter |
| `force_ice_relay` | User ID (e.g. `user_3`) | — | `TURN` | Route user through TURN relay |
| `adjust_bitrate` | User ID (e.g. `user_3`) | — | Bitrate (kbps) | Adjust video bitrate cap |

```python
from webrtc_ops_env.models import WebRTCAction

action = WebRTCAction(
    command="modify_config",
    target="signaling.yaml",
    key="port",
    value="8081"
)
```

## 👁️ Observation Space

After each step, the agent receives:

| Field | Type | Description |
|-------|------|-------------|
| `terminal_output` | `str` | Simulated CLI output from the last command |
| `system_logs` | `List[str]` | Last 10 lines of simulated server logs |
| `network_metrics` | `Dict` | Per-user metrics: packet_loss, jitter, bitrate, relay_type |

## 📋 Tasks

### Task 1: Port Mismatch (Easy) ⭐
**Scenario:** The client tries to connect to port 8081, but the signaling server is configured on port 8080. Logs show repeated `[WARN] Connection refused` messages.

**Expected solution:**
1. `read_logs(target="signaling.yaml")` — Discover the port mismatch
2. `modify_config(target="signaling.yaml", key="port", value="8081")` — Fix the port
3. `restart_signaling()` — Apply the change

**Grading:** Score 1.0 if port is fixed AND service is restarted.

---

### Task 2: SDP Codec Clash (Medium) ⭐⭐
**Scenario:** Connection established but one-way audio bug. The client enforces PCMU while the server only allows Opus. Logs show `[ERROR] SDP Negotiation failed: No matching payload type`.

**Expected solution:**
1. `read_logs(target="system")` — See the SDP error
2. `read_logs(target="sdp")` — Inspect the SDP offer
3. `modify_config(target="signaling.yaml", key="allowed_codecs", value='["Opus", "PCMU"]')` — Add PCMU

**Grading:** Score 1.0 if codecs are compatible and audio bitrate recovers to 48 kbps.

---

### Task 3: Congestion Degradation (Hard) ⭐⭐⭐
**Scenario:** 4-user session. user_3 has 35% packet loss on a direct P2P (host) ICE candidate. Logs show `[WARN] NACK bursts detected for user_3`.

**Expected solution:**
1. `force_ice_relay(target="user_3", value="TURN")` — Route through TURN server (+0.5)
2. `adjust_bitrate(target="user_3", value="250")` — Reduce video quality (+0.5)

**Grading:** Partial scoring — 0.5 for TURN relay + 0.5 for appropriate bitrate reduction.

## 📊 Reward Function

The environment provides **continuous reward signals**, not just binary end-of-episode scoring:

| Signal | Reward |
|--------|--------|
| Valid syntactic action (no error) | +0.1 |
| Correct diagnostic read | +0.0 (information gathering) |
| Partial progress toward fix | +0.2 to +0.4 |
| Task fully solved | Remaining to 1.0 |
| Destructive action | -0.2 |
| Invalid parameter | -0.1 |

## 🚀 Setup

### Install the client
```bash
pip install git+https://huggingface.co/spaces/pheelip0030/webrtc-ops-env
```

### Or install from source
```bash
cd webrtc_ops_env
pip install -e .
```

### Run the server locally
```bash
cd webrtc_ops_env
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

### Run with Docker
```bash
cd webrtc_ops_env
docker build -t webrtc-ops-env server/
docker run -p 8000:8000 webrtc-ops-env
```

## 📄 Usage

### MCP Tool Calling (Recommended)
```python
from webrtc_ops_env import WebRTCOpsEnv

with WebRTCOpsEnv(base_url="http://localhost:8000").sync() as env:
    env.reset(task_name="port_mismatch")
    
    # Discover available tools
    tools = env.list_tools()
    for tool in tools:
        print(f"{tool.name}: {tool.description}")
    
    # Diagnose
    result = env.call_tool("read_logs", target="signaling.yaml")
    print(result)
    
    # Fix
    env.call_tool("modify_config", target="signaling.yaml", key="port", value="8081")
    env.call_tool("restart_signaling")
```

### Async Usage
```python
import asyncio
from webrtc_ops_env import WebRTCOpsEnv

async def main():
    async with WebRTCOpsEnv(base_url="http://localhost:8000") as env:
        await env.reset(task_name="sdp_codec_clash")
        result = await env.call_tool("read_logs", target="system")
        print(result)

asyncio.run(main())
```

## 🏃 Baseline Inference

```bash
export HF_TOKEN=your_token
export IMAGE_NAME=webrtc-ops-env
export WEBRTC_OPS_TASK=port_mismatch  # or omit to run all tasks

python inference.py
```

### Baseline Scores (Qwen/Qwen2.5-72B-Instruct)

| Task | Difficulty | Expected Score |
|------|-----------|---------------|
| port_mismatch | Easy | ~0.8–1.0 |
| sdp_codec_clash | Medium | ~0.5–0.8 |
| congestion_degradation | Hard | ~0.3–0.7 |

## 📁 Project Structure

```
webrtc_ops_env/
├── __init__.py          # Package exports
├── models.py            # Pydantic models (Action, Observation, State)
├── client.py            # WebRTCOpsEnv(MCPToolClient)
├── openenv.yaml         # OpenEnv manifest
├── pyproject.toml       # Dependencies
├── README.md            # This file
├── .dockerignore
└── server/
    ├── __init__.py
    ├── webrtc_environment.py  # Core environment logic
    ├── app.py                 # FastAPI server
    ├── Dockerfile             # Container image
    └── requirements.txt       # Docker dependencies
inference.py                   # Baseline inference script (repo root)
```

## 📜 License

BSD-3-Clause
