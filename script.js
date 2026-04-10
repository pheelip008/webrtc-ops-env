// Simulated playback of the Qwen AI solving the tasks!

const SCENARIOS = {
    'hard': [
        { delay: 1000, type: 'init_hard' },
        { delay: 2000, type: 'action', cmd: '{"command":"read_logs","target":"system"}', event: 'Reading system logs...' },
        { delay: 4500, type: 'log', text: 'Log analysis complete. Detected NACK bursts from user_3.' },
        { delay: 6000, type: 'action', cmd: '{"command":"read_logs","target":"metrics"}', event: 'Targeting network metrics payload' },
        { delay: 8500, type: 'log', text: 'Loss 35% on user_3 (host ice candidate). Action required: Force TURN relay.' },
        { delay: 10500, type: 'action', cmd: '{"command":"force_ice_relay","target":"user_3","value":"TURN"}', event: 'Executing infrastructure patch...' },
        { delay: 11000, type: 'update_graph', update: 'relay' },
        { delay: 13500, type: 'log', text: 'Relay established. Checking stream bitrate limits.' },
        { delay: 15500, type: 'action', cmd: '{"command":"adjust_bitrate","target":"user_3","value":500}', event: 'Modifying P2P limits' },
        { delay: 16000, type: 'update_graph', update: 'bitrate' },
        { delay: 18500, type: 'log', text: 'Agent completed optimization.' },
        { delay: 20000, type: 'finish' }
    ],
    'medium': [
        { delay: 1000, type: 'init_medium' },
        { delay: 2000, type: 'action', cmd: '{"command":"read_logs","target":"system"}', event: 'Reading system logs...' },
        { delay: 4500, type: 'log', text: 'Detected one-way audio bug. Client requested PCMU, server allows Opus only.' },
        { delay: 6000, type: 'action', cmd: '{"command":"modify_config","target":"signaling.yaml","key":"allowed_codecs","value":["Opus","PCMU"]}', event: 'Patching codec configuration' },
        { delay: 7000, type: 'update_config', code: `port: 8080\nhost: '0.0.0.0'\ntls: true\nlog_level: 'debug'\nmax_connections: 200\nallowed_codecs:\n  - Opus\n  - PCMU` },
        { delay: 9000, type: 'action', cmd: '{"command":"restart_signaling"}', event: 'Rebooting WebRTC Signaling Server' },
        { delay: 9500, type: 'update_graph', update: 'codec_fix' },
        { delay: 11500, type: 'log', text: 'SDP negotiation successful. Audio bitrate recovered.' },
        { delay: 13000, type: 'finish' }
    ],
    'easy': [
        { delay: 1000, type: 'init_easy' },
        { delay: 2000, type: 'action', cmd: '{"command":"read_logs","target":"system"}', event: 'Reading system logs...' },
        { delay: 4500, type: 'log', text: 'Connection refused errors detected on port 8081. Server is on 8080.' },
        { delay: 6000, type: 'action', cmd: '{"command":"modify_config","target":"signaling.yaml","key":"port","value":8081}', event: 'Patching socket port' },
        { delay: 7000, type: 'update_config', code: `port: 8081\nhost: '0.0.0.0'\ntls: false\nlog_level: 'info'\nmax_connections: 100` },
        { delay: 9000, type: 'action', cmd: '{"command":"restart_signaling"}', event: 'Rebooting WebRTC Signaling Server' },
        { delay: 9500, type: 'update_graph', update: 'port_fix' },
        { delay: 11500, type: 'log', text: 'Server restarted on 8081. Client connections established.' },
        { delay: 13000, type: 'finish' }
    ]
};

document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('start-btn');
    const taskSelector = document.getElementById('task-selector');
    const terminal = document.getElementById('terminal-output');
    const statusText = document.getElementById('env-status');
    const statusDot = document.querySelector('.pulse-dot');
    const flyout = document.getElementById('action-flyout');
    const actionText = document.getElementById('action-text');
    const configCode = document.getElementById('config-code');
    const gradeBadge = document.getElementById('grade-badge');

    // UI Elements
    const node1 = document.getElementById('node-user_1');
    const node2 = document.getElementById('node-user_2');
    const node3 = document.getElementById('node-user_3');
    const node4 = document.getElementById('node-user_4');
    
    const metric3 = document.getElementById('metric-user_3');
    const relay3 = document.getElementById('relay-user_3');
    const line3 = document.getElementById('line-user_3');
    
    const healthStatus = document.getElementById('health-status');
    const taskLabel = document.querySelector('.metrics-bar .metric strong.text-dark');

    // Make elements available for global changes
    const allLines = document.querySelectorAll('.connections line');
    const allNodes = [node1, node2, node3, node4];

    function appendLog(text, className) {
        const div = document.createElement('div');
        div.className = `log-line ${className}`;
        div.textContent = text;
        terminal.appendChild(div);
        terminal.scrollTop = terminal.scrollHeight;
    }

    function showFlyout(text) {
        actionText.textContent = text;
        flyout.classList.add('visible');
        setTimeout(() => flyout.classList.remove('visible'), 2000);
    }

    // Reset visual state based on task
    function resetVisuals(task) {
        gradeBadge.classList.add('hidden');
        
        if (task === 'hard') {
            taskLabel.textContent = 'congestion_degradation';
            healthStatus.textContent = 'Critical';
            healthStatus.className = 'text-error';
            configCode.textContent = "port: 8080\nhost: '0.0.0.0'\ntls: true\nlog_level: 'warn'\nmax_connections: 500\nice_servers:\n  - urls: 'stun:stun.example.com:3478'\n  - urls: 'turn:turn.example.com:3478'";
            
            // Nodes state
            allNodes.forEach(n => { n.style.display = 'flex'; n.className = 'node user-node stable'; });
            node3.className = 'node user-node degraded pulse-error';
            metric3.textContent = 'Loss: 35.0%';
            relay3.textContent = 'host';
            relay3.className = 'relay-tag';
            relay3.style.display = 'block';

            // Lines state
            allLines.forEach(l => l.className.baseVal = 'line-stable');
            line3.className.baseVal = 'line-degraded error-anim';
            document.getElementById('metric-user_1').textContent = 'Loss: 1.2%';
            document.getElementById('metric-user_2').textContent = 'Loss: 0.8%';
            document.getElementById('metric-user_4').textContent = 'Loss: 2.0%';
        }
        else if (task === 'medium') {
            taskLabel.textContent = 'sdp_codec_clash';
            healthStatus.textContent = 'No Audio Sync';
            healthStatus.className = 'text-warning';
            configCode.textContent = "port: 8080\nhost: '0.0.0.0'\ntls: true\nlog_level: 'debug'\nmax_connections: 200\nallowed_codecs:\n  - Opus";
            
            // Codec clash affects only User 1 audio
            allNodes.forEach(n => { n.style.display = 'none'; n.className = 'node user-node stable'; });
            node1.style.display = 'flex';
            node1.className = 'node user-node degraded pulse-error';
            relay3.style.display = 'none'; // hide relays
            
            document.getElementById('metric-user_1').textContent = 'PT=0 (PCMU) Rejected';
            
            allLines.forEach(l => l.className.baseVal = 'line-stable');
            document.querySelector('line[x1="15%"][y1="15%"]').className.baseVal = 'line-degraded error-anim';
        }
        else if (task === 'easy') {
            taskLabel.textContent = 'port_mismatch';
            healthStatus.textContent = 'Offline (Connection Refused)';
            healthStatus.className = 'text-error';
            configCode.textContent = "port: 8080\nhost: '0.0.0.0'\ntls: false\nlog_level: 'info'\nmax_connections: 100";
            
            // All disconnected
            allNodes.forEach(n => { n.style.display = 'flex'; n.className = 'node user-node degraded'; });
            allNodes.forEach((n, i) => document.getElementById(`metric-user_${i+1}`).textContent = 'Socket Error');
            relay3.style.display = 'none';
            allLines.forEach(l => l.className.baseVal = 'line-degraded error-anim');
        }
    }

    startBtn.addEventListener('click', () => {
        // Reset state
        const selectedTask = taskSelector.value;
        startBtn.disabled = true;
        taskSelector.disabled = true;
        terminal.innerHTML = '<div class="log-line text-muted">Awaiting LLM Inference stream...</div>';
        statusText.textContent = "Session Active";
        statusDot.classList.add('active');

        // Playback sequence
        SCENARIOS[selectedTask].forEach(step => {
            setTimeout(() => {
                if (step.type.startsWith('init')) {
                    resetVisuals(selectedTask);
                    appendLog(`[INFO] Evaluating environment parameters for ${selectedTask}...`, '');
                }
                else if (step.type === 'log') {
                    appendLog(`[INFO] ${step.text}`, '');
                } 
                else if (step.type === 'action') {
                    appendLog(`► Generating Tool Call:`, 'cmd');
                    appendLog(`${step.cmd}`, 'json');
                    showFlyout(step.event);
                }
                else if (step.type === 'update_config') {
                    configCode.textContent = step.code;
                    configCode.parentElement.classList.remove('highlight-update');
                    void configCode.parentElement.offsetWidth; // trigger reflow
                    configCode.parentElement.classList.add('highlight-update');
                    appendLog(`[MCP] Success: Configuration file patched`, '');
                }
                else if (step.type === 'update_graph') {
                    if (step.update === 'relay') {
                        relay3.textContent = 'TURN';
                        relay3.classList.add('turn');
                        healthStatus.textContent = 'Stabilizing...';
                        healthStatus.className = 'text-warning';
                        appendLog(`[MCP] Success: ICE relay forced to TURN`, '');
                    }
                    if (step.update === 'bitrate') {
                        metric3.textContent = 'Loss: 2.1%';
                        node3.className = 'node user-node fixed';
                        line3.className.baseVal = 'line-fixed';
                        healthStatus.textContent = 'Nominal';
                        healthStatus.className = 'text-success';
                        appendLog(`[MCP] Success: Bitrate reduced to 500kbps`, '');
                    }
                    if (step.update === 'codec_fix') {
                        document.getElementById('metric-user_1').textContent = 'Codec: PCMU synced';
                        node1.className = 'node user-node fixed';
                        document.querySelector('line[x1="15%"][y1="15%"]').className.baseVal = 'line-fixed';
                        healthStatus.textContent = 'Nominal';
                        healthStatus.className = 'text-success';
                        appendLog(`[MCP] Success: Signaling server online.`, '');
                    }
                    if (step.update === 'port_fix') {
                        allNodes.forEach((n, i) => document.getElementById(`metric-user_${i+1}`).textContent = 'Socket Connected');
                        allNodes.forEach(n => n.className = 'node user-node fixed');
                        allLines.forEach(l => l.className.baseVal = 'line-fixed');
                        healthStatus.textContent = 'Nominal';
                        healthStatus.className = 'text-success';
                        appendLog(`[MCP] Success: Signaling server online.`, '');
                    }
                }
                else if (step.type === 'finish') {
                    appendLog(`[END] Evaluation complete. Task resolved.`, 'cmd');
                    statusText.textContent = "Environment Suspended";
                    statusDot.classList.remove('active');
                    startBtn.disabled = false;
                    taskSelector.disabled = false;
                    startBtn.innerHTML = '<i data-lucide="rotate-ccw"></i> Reset Environment';
                    lucide.createIcons();
                    
                    gradeBadge.classList.remove('hidden');
                }
            }, step.delay);
        });
    });

    // Initial visual setup
    resetVisuals(taskSelector.value);
    taskSelector.addEventListener('change', () => {
        resetVisuals(taskSelector.value);
        startBtn.innerHTML = '<i data-lucide="play"></i> Start Inference';
        terminal.innerHTML = '<div class="log-line text-muted">Initialize OpenEnv Session...</div><div class="log-line text-muted">Agent connection standby.</div>';
        lucide.createIcons();
    });
});
