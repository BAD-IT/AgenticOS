const escapeHtml = (str) => {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
};

const cliInput = document.getElementById('cli-input');
const chatHistory = document.getElementById('chat-history');
const terminalFeed = document.getElementById('terminal-feed');
const workspacesContainer = document.getElementById('workspaces');
const addWorkspaceBtn = document.getElementById('add-workspace-btn');
const contextContent = document.getElementById('context-content');

const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

let currentWorkspace = 1;
let totalWorkspaces = 1;

// Resizer logic
let isDraggingLeft = false;
let isDraggingRight = false;
const leftPanel = document.getElementById('left-panel');
const rightPanel = document.getElementById('right-panel');
const flexContainer = document.getElementById('flex-container');
const resizerLeft = document.getElementById('resizer-left');
const resizerRight = document.getElementById('resizer-right');

resizerLeft.addEventListener('mousedown', () => { isDraggingLeft = true; resizerLeft.classList.add('dragging'); });
resizerRight.addEventListener('mousedown', () => { isDraggingRight = true; resizerRight.classList.add('dragging'); });

document.addEventListener('mousemove', (e) => {
    if (isDraggingLeft) {
        let newWidth = e.clientX - flexContainer.offsetLeft - 15;
        if (newWidth > 100 && newWidth < flexContainer.offsetWidth - 200) {
            leftPanel.style.width = `${newWidth}px`;
        }
    }
    if (isDraggingRight) {
        let newWidth = flexContainer.offsetWidth - (e.clientX - flexContainer.offsetLeft) - 15;
        if (newWidth > 100 && newWidth < flexContainer.offsetWidth - 200) {
            rightPanel.style.width = `${newWidth}px`;
        }
    }
});

document.addEventListener('mouseup', () => {
    isDraggingLeft = false;
    isDraggingRight = false;
    resizerLeft.classList.remove('dragging');
    resizerRight.classList.remove('dragging');
});

// Quick commands & greetings
const GREETINGS = ["hi", "hello", "hey", "sup", "greetings"];

const handleQuickCommand = (cmd) => {
    const text = cmd.trim().toLowerCase();
    
    if (GREETINGS.includes(text)) {
        appendChat("Hello! I am Agentic OS. How can I assist you in this workspace?", 'agent');
        return true;
    }
    
    switch(text) {
        case '/clear':
            chatHistory.innerHTML = '';
            return true;
        case '/session':
            appendChat('System Session Metadata: Workspace ' + currentWorkspace, 'system');
            return true;
        case '/stats':
            appendChat('Hardware Stats: VRAM 12GB/16GB, CPU 15%', 'system');
            return true;
        case '/joke':
            appendChat('Why do programmers prefer dark mode? Because light attracts bugs.', 'agent');
            return true;
        case '/time':
            appendChat('Local system time: ' + new Date().toLocaleTimeString(), 'agent');
            return true;
        default:
            return false;
    }
};

const appendChat = (text, sender) => {
    const div = document.createElement('div');
    div.className = `chat-msg ${sender}`;
    div.innerText = `> ${text}`;
    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
};

const appendLog = (level, text) => {
    const div = document.createElement('div');
    div.className = `log-line log-${level}`;
    div.innerText = `[${level.toUpperCase()}] ${text}`;
    terminalFeed.appendChild(div);
    terminalFeed.scrollTop = terminalFeed.scrollHeight;
};

// Input handling
cliInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && cliInput.value) {
        const val = cliInput.value;
        appendChat(val, 'user');
        cliInput.value = '';
        if (!handleQuickCommand(val)) {
            // Show loading indicator
            const loader = document.getElementById('chat-loading-indicator');
            if (loader) {
                loader.style.display = 'flex';
                loader.querySelector('.loader-text').innerText = 'Agent is thinking...';
            }
            
            fetch(`/api/v1/tasks/submit?workspace_id=${currentWorkspace}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    task_id: crypto.randomUUID ? crypto.randomUUID() : "task-" + Date.now(),
                    intent: val,
                    status: "PENDING",
                    parameters: {}
                })
            }).then(async res => {
                if (!res.ok) {
                    const err = await res.text();
                    throw new Error(`HTTP ${res.status}: ${err}`);
                }
            }).catch(err => {
                appendChat('Error submitting task: ' + err.message, 'system');
                if (loader) loader.style.display = 'none';
            });
        }
    }
});

const loadWorkspaceHistory = async (wsNum) => {
    try {
        const res = await fetch(`/api/v1/workspaces/${wsNum}/history`);
        const data = await res.json();
        chatHistory.innerHTML = '';
        if (data.history) {
            data.history.forEach(item => {
                let parsed = item.payload;
                if (typeof parsed === 'string') parsed = JSON.parse(parsed);
                // Each row represents one task: the original intent (user) plus,
                // once processed, the agent's response merged into the same payload.
                appendChat(parsed.intent || JSON.stringify(parsed), 'user');
                if (parsed.response || parsed.action || parsed.message) {
                    appendChat(parsed.response || parsed.action || parsed.message, 'agent');
                }
            });
        }
        appendChat(`Switched to Workspace ${wsNum}`, 'system');
    } catch (e) {
        console.error("Failed to load history", e);
        appendChat(`Switched to Workspace ${wsNum}`, 'system');
    }
};

const switchWorkspace = (wsNum) => {
    if (wsNum > totalWorkspaces || wsNum < 1) return;
    document.querySelectorAll('.workspace').forEach(w => w.classList.remove('active'));
    document.querySelector(`[data-ws="${wsNum}"]`).classList.add('active');
    currentWorkspace = wsNum;
    document.getElementById('status').innerHTML = `Agentic OS - Workspace ${wsNum}`;
    loadWorkspaceHistory(wsNum);
    fetchDebugTraces();
    lastLiveTaskId = null; // force a fresh task separator on the next live event for this workspace
    liveDebugActive = false; // allow REST fetch for the new workspace
};

// Bind clicks to existing workspace tabs
document.querySelectorAll('.workspace').forEach(w => {
    w.addEventListener('click', (e) => switchWorkspace(parseInt(e.target.getAttribute('data-ws'))));
});

// Add new workspace
addWorkspaceBtn.addEventListener('click', () => {
    if (totalWorkspaces >= 10) {
        appendChat('Maximum of 10 workspaces reached.', 'system');
        return;
    }
    totalWorkspaces++;
    const span = document.createElement('span');
    span.className = 'workspace';
    span.setAttribute('data-ws', totalWorkspaces);
    span.innerText = totalWorkspaces;
    span.addEventListener('click', (e) => switchWorkspace(parseInt(e.target.getAttribute('data-ws'))));
    workspacesContainer.insertBefore(span, addWorkspaceBtn);
    switchWorkspace(totalWorkspaces);
});

// Workspace switching via Alt+1 to Alt+0
window.addEventListener('keydown', (e) => {
    if (e.altKey && e.key >= '0' && e.key <= '9') {
        e.preventDefault();
        const wsNum = e.key === '0' ? 10 : parseInt(e.key);
        if (wsNum <= totalWorkspaces) {
            switchWorkspace(wsNum);
        }
    }
});

// Tab Switching Logic
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        // Remove active class from all buttons and contents
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.style.display = 'none');
        
        // Add active class to clicked button
        btn.classList.add('active');
        
        // Show corresponding content
        const targetId = btn.getAttribute('data-target');
        const targetContent = document.getElementById(targetId);
        if (targetContent) {
            targetContent.style.display = 'flex';
        }
        
        // Scroll to bottom if switching back to chat or terminal
        if (targetId === 'chat-tab') chatHistory.scrollTop = chatHistory.scrollHeight;
        if (targetId === 'telemetry-tab') terminalFeed.scrollTop = terminalFeed.scrollHeight;

        if (targetId === 'database-tab') {
            fetchDB();
        }
        if (targetId === 'debug-tab') {
            fetchDebugTraces();
        }
    });
});

// WebSockets
let notifSocket, chatSocket;

const connectSockets = () => {
    notifSocket = new WebSocket(`ws://${location.host}/api/v1/stream/notifications`);
    notifSocket.onmessage = (e) => {
        try {
            const row = JSON.parse(e.data);
            if (row && row.payload) {
                const p = typeof row.payload === 'string' ? JSON.parse(row.payload) : row.payload;
                if (p.icon && p.category) {
                    appendTelemetry(p.icon, p.category, p.message || '', p.type || 'info', row);
                    // Update loading indicator text if it's visible
                    const loader = document.getElementById('chat-loading-indicator');
                    if (loader && loader.style.display !== 'none') {
                        loader.querySelector('.loader-text').innerText = `${p.icon} ${p.category}: ${p.message || ''}`;
                    }
                } else {
                    appendLog(p.level || 'info', p.message || JSON.stringify(p));
                }
            }
        } catch(err) {
            console.error(err);
        }
    };

    chatSocket = new WebSocket(`ws://${location.host}/api/v1/stream/chat`);
    chatSocket.onmessage = (e) => {
        try {
            const row = JSON.parse(e.data);
            if (row && row.payload) {
                const p = typeof row.payload === 'string' ? JSON.parse(row.payload) : row.payload;
                if (p.status === 'REQUIRES_CLARIFICATION') {
                    appendChat(p.message || 'Clarification required.', 'system');
                } else if (p.action || p.message || p.response) {
                    appendChat(p.action || p.message || p.response, 'agent');
                }
                
                // Only hide the loader once the task has actually finished (RESULT_OUTPUT/ERROR),
                // not on the initial USER_INPUT/PENDING notification fired right after submission.
                if (p.status === 'RESULT_OUTPUT' || p.status === 'ERROR' || p.status === 'REQUIRES_CLARIFICATION') {
                    const loader = document.getElementById('chat-loading-indicator');
                    if (loader) loader.style.display = 'none';
                }
                
                // If a task changed state, re-fetch queues and debug traces
                fetchQueues();
                fetchDebugTraces();
            }
        } catch(err) {
            console.error(err);
        }
    };
};

connectSockets();

// Always focus input
document.addEventListener('click', (e) => {
    if (e.target.tagName !== 'BUTTON' && !e.target.classList.contains('resizer') && !e.target.classList.contains('workspace')) {
        cliInput.focus();
    }
});
cliInput.focus();
loadWorkspaceHistory(currentWorkspace);

// --- Modal Logic ---
const payloadModal = document.getElementById('payload-modal');
const modalTitle = document.getElementById('modal-title');
const modalBodyContent = document.getElementById('modal-body-content');
const closeModalBtn = document.getElementById('close-modal');

if (closeModalBtn) {
    closeModalBtn.addEventListener('click', () => {
        payloadModal.style.display = 'none';
    });
}

window.addEventListener('click', (e) => {
    if (e.target === payloadModal) {
        payloadModal.style.display = 'none';
    }
});

// Settings Modal Logic
const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const closeSettingsBtn = document.getElementById('close-settings-modal');
const settingsBody = document.getElementById('settings-modal-body');

if (settingsBtn && settingsModal) {
    settingsBtn.addEventListener('click', async () => {
        settingsModal.style.display = 'flex';
        settingsBody.innerHTML = 'Loading configuration...';
        try {
            const res = await fetch('/api/v1/settings');
            const data = await res.json();
            
            let html = '<div style="display:flex;flex-direction:column;gap:10px;">';
            for (const [key, val] of Object.entries(data)) {
                html += `
                    <div style="display:flex;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:5px;">
                        <span style="color:#94a3b8">${escapeHtml(key)}</span>
                        <span style="font-family:var(--font-mono);font-size:12px;">${escapeHtml(String(val))}</span>
                    </div>
                `;
            }
            html += '</div>';
            settingsBody.innerHTML = html;
        } catch (e) {
            settingsBody.innerHTML = `<span style="color:#ef4444">Error loading settings.</span>`;
        }
    });

    closeSettingsBtn.addEventListener('click', () => {
        settingsModal.style.display = 'none';
    });

    window.addEventListener('click', (e) => {
        if (e.target === settingsModal) {
            settingsModal.style.display = 'none';
        }
    });
}

// --- TELEMETRY RENDERER ---
const appendTelemetry = (icon, category, message, type = 'info', rawRow = null) => {
    const div = document.createElement('div');
    div.className = `telemetry-item ${type}`;
    div.innerHTML = `<span class="icon">${escapeHtml(icon)}</span> <strong class="category">${escapeHtml(category)}:</strong> <span class="message">${escapeHtml(message)}</span>`;
    
    if (category.includes('File') || category.includes('DB') || category.includes('State')) {
        div.style.cursor = 'pointer';
        div.title = 'Click to view payload details';
        div.addEventListener('click', () => {
            if (payloadModal) {
                modalTitle.innerText = `${icon} ${category}`;
                const payloadData = rawRow ? JSON.stringify(rawRow, null, 2) : "{}";
                modalBodyContent.innerHTML = `<strong>Target:</strong> ${message}\n\n<span style="color:#94a3b8">/* Live Payload Data */</span>\n${payloadData}`;
                payloadModal.style.display = 'flex';
            }
        });
    }
    
    terminalFeed.appendChild(div);
    terminalFeed.scrollTop = terminalFeed.scrollHeight;
};

// --- DATABASE TAB ---
const dbTable = document.getElementById('db-table');
const dbSelect = document.getElementById('db-table-select');
const dbSearch = document.getElementById('db-search');
const dbRefreshBtn = document.getElementById('db-refresh-btn');

const fetchDB = async () => {
    if (!dbTable) return;
    try {
        const res = await fetch(`/api/v1/db/query?table=${dbSelect.value}&search=${encodeURIComponent(dbSearch.value)}`);
        const result = await res.json();
        if (result.data && result.data.length > 0) {
            const keys = Object.keys(result.data[0]);
            let html = `<thead><tr style="border-bottom:1px solid #334155;">`;
            keys.forEach(k => html += `<th style="padding:5px; text-align:left;">${k}</th>`);
            html += `</tr></thead><tbody>`;
            result.data.forEach(row => {
                html += `<tr style="border-bottom:1px solid rgba(255,255,255,0.05);">`;
                keys.forEach(k => {
                    let val = row[k];
                    if (typeof val === 'object') val = JSON.stringify(val);
                    const safeVal = escapeHtml(String(val));
                    html += `<td style="padding:5px; max-width:200px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${safeVal}">${safeVal}</td>`;
                });
                html += `</tr>`;
            });
            html += `</tbody>`;
            dbTable.innerHTML = html;
        } else {
            dbTable.innerHTML = `<tr><td>No data found.</td></tr>`;
        }
    } catch (err) {
        dbTable.innerHTML = `<tr><td style="color:#ef4444;">Error fetching data.</td></tr>`;
    }
};
if (dbRefreshBtn) dbRefreshBtn.addEventListener('click', fetchDB);
if (dbSearch) dbSearch.addEventListener('keypress', (e) => { if (e.key === 'Enter') fetchDB(); });
if (dbSelect) dbSelect.addEventListener('change', fetchDB);

// --- WORKSPACE EXPLORER ---
const inboxTree = document.getElementById('inbox-tree');
const outboxTree = document.getElementById('outbox-tree');

const fetchWorkspaceFiles = async () => {
    if (!inboxTree || !outboxTree) return;
    try {
        const res = await fetch('/api/v1/workspace/files');
        const data = await res.json();
        
        const renderTree = (files, ul) => {
            if (!files || files.length === 0) {
                ul.innerHTML = `<li style="color:#64748b; font-style:italic;">Empty</li>`;
                return;
            }
            ul.innerHTML = files.map(f => `<li style="margin-bottom:3px;">📄 ${f}</li>`).join('');
        };
        renderTree(data.inbox, inboxTree);
        renderTree(data.outbox, outboxTree);
    } catch (e) {
        console.error("Failed to load workspace files", e);
    }
};

// Auto-refresh DB and Files every 10 seconds if active
setInterval(() => {
    if (document.getElementById('database-tab') && document.getElementById('database-tab').style.display === 'flex') {
        fetchDB();
    }
    if (inboxTree) fetchWorkspaceFiles();
}, 10000);

const updateQueueCounts = (counts) => {
    let ingest = (counts['USER_INPUT'] || 0) + (counts['TASK'] || 0);
    let process = (counts['PENDING'] || 0) + (counts['EMBEDDING'] || 0) + (counts['IO_WAIT'] || 0);
    let valid = (counts['REVIEW'] || 0);
    let out = (counts['RESULT_OUTPUT'] || 0) + (counts['NOTIFICATION'] || 0);
    let err = (counts['ERROR'] || 0);

    const elIngest = document.getElementById('queue-ingest');
    const elProcess = document.getElementById('queue-process');
    const elValid = document.getElementById('queue-valid');
    const elOut = document.getElementById('queue-out');
    const elErr = document.getElementById('queue-error');
    const elErrCont = document.getElementById('queue-error-container');

    if (elIngest) elIngest.innerText = ingest;
    if (elProcess) elProcess.innerText = process;
    if (elValid) elValid.innerText = valid;
    if (elOut) elOut.innerText = out;
    if (elErr && elErrCont) {
        elErr.innerText = err;
        elErrCont.style.display = err > 0 ? "block" : "none";
    }
};

const fetchQueues = async () => {
    try {
        const res = await fetch(`/api/v1/telemetry/queues`);
        const data = await res.json();
        if (data.queues) {
            updateQueueCounts(data.queues);
        }
    } catch(e) {
        console.error("Failed to fetch queue counts", e);
    }
};

const fetchDebugTraces = async () => {
    const debugFeed = document.getElementById('debug-feed');
    const cognitiveTrace = document.getElementById('cognitive-trace-feed');
    if (!debugFeed) return;
    // Skip REST re-render while the WebSocket is actively streaming live events
    if (liveDebugActive) return;
    
    try {
        const res = await fetch(`/api/v1/debug/traces/${currentWorkspace}`);
        if (!res.ok) throw new Error('Failed to fetch traces');
        const data = await res.json();
        const traces = data.traces || [];
        
        if (traces.length === 0) {
            debugFeed.innerHTML = '<div style="color: #64748b; font-style: italic;">No active trace...</div>';
            if (cognitiveTrace) cognitiveTrace.innerHTML = '<div style="color: #64748b; font-style: italic;">No active trace...</div>';
            return;
        }
        
        let htmlFull = '';
        let htmlMinimal = '';
        let prevTaskId = null;
        
        traces.forEach(trace => {
            if (trace.task_id !== prevTaskId) {
                const shortId = (trace.task_id || 'unknown').split('-')[0];
                const sepHtml = `
                    <div style="display:flex; align-items:center; gap:8px; margin:12px 0; color:#64748b; font-size:10px; text-transform:uppercase; letter-spacing:1px;">
                        <div style="flex-grow:1; height:1px; background:rgba(255,255,255,0.12);"></div>
                        <span>&#9654; New Task ${shortId}</span>
                        <div style="flex-grow:1; height:1px; background:rgba(255,255,255,0.12);"></div>
                    </div>
                `;
                htmlFull += sepHtml;
                htmlMinimal += sepHtml;
                prevTaskId = trace.task_id;
            }
            const timeStr = new Date(trace.created_at).toLocaleTimeString();
            let nodeColor = '#3b82f6'; // default blue
            let icon = '⚙️';
            if (trace.node_name.toLowerCase().includes('error') || trace.node_name.toLowerCase().includes('fallback')) {
                nodeColor = '#ef4444'; // red
                icon = '⚠️';
            } else if (trace.node_name.toLowerCase().includes('result')) {
                nodeColor = '#22c55e'; // green
                icon = '✅';
            } else if (trace.node_name.toLowerCase().includes('review')) {
                nodeColor = '#a855f7'; // purple
                icon = '🔍';
            }
            
            // Format state diff
            let diffHtml = '';
            if (trace.state_diff) {
                try {
                    const diffObj = typeof trace.state_diff === 'string' ? JSON.parse(trace.state_diff) : trace.state_diff;
                    diffHtml = `<pre style="margin-top:5px; padding:8px; background:rgba(0,0,0,0.4); border-radius:4px; overflow-x:auto; font-size:11px;">${JSON.stringify(diffObj, null, 2)}</pre>`;
                } catch(e) {
                    diffHtml = `<div style="margin-top:5px; color:#94a3b8;">${trace.state_diff}</div>`;
                }
            }
            
            // Full UI
            htmlFull += `
                <div style="margin-bottom:15px; border-left:2px solid ${nodeColor}; padding-left:10px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                        <span style="color:${nodeColor}; font-weight:bold;">${icon} [${trace.node_name}]</span>
                        <span style="color:#64748b; font-size:10px;">${timeStr} | Task: ${trace.task_id.split('-')[0]}</span>
                    </div>
                    ${diffHtml}
                </div>
            `;
            
            // Minimal UI (Left Panel)
            htmlMinimal += `
                <div style="border-left:2px solid ${nodeColor}; padding-left:5px; margin-bottom:5px;">
                    <span style="color:${nodeColor};">${icon} [${trace.node_name}]</span>
                    <div style="color:#64748b; font-size:10px;">${timeStr}</div>
                </div>
            `;
        });
        
        debugFeed.innerHTML = htmlFull;
        if (cognitiveTrace) {
            cognitiveTrace.innerHTML = htmlMinimal;
            // Scroll to bottom
            cognitiveTrace.scrollTop = cognitiveTrace.scrollHeight;
        }
        // Scroll to bottom for full feed
        debugFeed.scrollTop = debugFeed.scrollHeight;
        
    } catch (e) {
        console.error("Failed to load debug traces:", e);
        debugFeed.innerHTML = '<div style="color: #ef4444;">Failed to load traces.</div>';
    }
};

const clearDebugBtn = document.getElementById('clear-debug-btn');
if (clearDebugBtn) {
    clearDebugBtn.addEventListener('click', () => {
        const debugFeed = document.getElementById('debug-feed');
        if (debugFeed) debugFeed.innerHTML = '<div style="color: #64748b; font-style: italic;">Cleared. Awaiting state events...</div>';
        liveDebugActive = false;
    });
}

fetchDB();
fetchWorkspaceFiles();
fetchQueues();
fetchDebugTraces();

// --- LOGS WEBSOCKET ---
let logSocket;
const connectLogSocket = () => {
    const logFeed = document.getElementById('log-feed');
    if (!logFeed) return;
    
    // Close existing socket if reconnecting
    if (logSocket) logSocket.close();
    
    // Clear the feed
    logFeed.innerHTML = "";
    
    const logSelect = document.getElementById('log-file-select');
    const logName = logSelect ? logSelect.value : 'api';
    
    logSocket = new WebSocket(`ws://${location.host}/api/v1/stream/logs/${logName}`);
    logSocket.onmessage = (e) => {
        const line = e.data;
        const searchVal = document.getElementById('log-search')?.value.toLowerCase();
        if (searchVal && !line.toLowerCase().includes(searchVal)) return;
        
        const div = document.createElement('div');
        div.innerText = line;
        logFeed.appendChild(div);
        
        // Auto-scroll
        if (logFeed.scrollHeight - logFeed.scrollTop < logFeed.clientHeight + 100) {
            logFeed.scrollTop = logFeed.scrollHeight;
        }
    };
    logSocket.onclose = () => {
        // Only auto-reconnect if it wasn't a deliberate change
        setTimeout(connectLogSocket, 5000);
    };
};

document.getElementById('log-file-select')?.addEventListener('change', connectLogSocket);

connectLogSocket();

// --- DEBUG TRACE WEBSOCKET ---
let debugSocket;
let lastLiveTaskId = null;
let liveDebugActive = false;
const buildTaskSeparator = (taskId) => {
    const shortId = (taskId || 'unknown').split('-')[0];
    const sep = document.createElement('div');
    sep.style.display = 'flex';
    sep.style.alignItems = 'center';
    sep.style.gap = '8px';
    sep.style.margin = '12px 0';
    sep.style.color = '#64748b';
    sep.style.fontSize = '10px';
    sep.style.textTransform = 'uppercase';
    sep.style.letterSpacing = '1px';
    sep.innerHTML = `
        <div style="flex-grow:1; height:1px; background:rgba(255,255,255,0.12);"></div>
        <span>&#9654; New Task ${shortId}</span>
        <div style="flex-grow:1; height:1px; background:rgba(255,255,255,0.12);"></div>
    `;
    return sep;
};

const connectDebugSocket = () => {
    const traceFeed = document.getElementById('cognitive-trace-feed');
    const debugFeed = document.getElementById('debug-feed');
    if (!debugFeed) return;
    
    debugSocket = new WebSocket(`ws://${location.host}/api/v1/stream/debug`);
    debugSocket.onmessage = (e) => {
        try {
            const data = JSON.parse(e.data);
            const diff = data.state_diff ? JSON.parse(data.state_diff) : {};
            
            const isNewTask = data.task_id !== lastLiveTaskId;
            lastLiveTaskId = data.task_id;
            liveDebugActive = true;
            
            // 1. Update Left Panel (Live Pulse)
            if (traceFeed) {
                // Clear placeholder if first event
                if (traceFeed.innerText.includes("No active trace")) {
                    traceFeed.innerHTML = "";
                }
                if (isNewTask) traceFeed.appendChild(buildTaskSeparator(data.task_id));
                const traceItem = document.createElement('div');
                traceItem.style.marginBottom = "4px";
                if (data.node_name === "Node_Worker_Thinking") {
                    traceItem.innerHTML = `<span style="color:#fbbf24;">[THINKING]</span> Evaluating intent & tools...`;
                } else if (data.node_name === "Node_Tool_Execution") {
                    traceItem.innerHTML = `<span style="color:#38bdf8;">[TOOL EXEC]</span> Running tools...`;
                } else if (data.node_name === "Node_Review") {
                    traceItem.innerHTML = `<span style="color:#a78bfa;">[REVIEW]</span> Checking outputs...`;
                } else if (data.node_name === "Node_Result") {
                    traceItem.innerHTML = `<span style="color:#34d399;">[RESULT]</span> Task finalized.`;
                } else {
                    traceItem.innerHTML = `<span style="color:#cbd5e1;">[${data.node_name}]</span> State updated.`;
                }
                traceFeed.appendChild(traceItem);
                traceFeed.scrollTop = traceFeed.scrollHeight;
            }
            
            // 2. Update Right Panel (Debug Deep Dive)
            // Clear placeholder if first event
            if (debugFeed.innerText.includes("Awaiting state events")) {
                debugFeed.innerHTML = "";
            }
            // Chronological order (oldest -> newest) so the task separator stays meaningful
            if (isNewTask) debugFeed.appendChild(buildTaskSeparator(data.task_id));
            const debugItem = document.createElement('div');
            debugItem.style.borderBottom = "1px solid rgba(255,255,255,0.1)";
            debugItem.style.paddingBottom = "10px";
            debugItem.style.marginBottom = "10px";
            debugItem.innerHTML = `
                <div style="color:#cbd5e1; font-weight:bold; margin-bottom:4px;">Node: ${data.node_name}</div>
                <div style="color:#94a3b8; font-size:10px;">${data.created_at || new Date().toISOString()}</div>
                <pre style="margin-top:5px; background:rgba(0,0,0,0.5); padding:8px; border-radius:4px; overflow-x:auto; color:#a78bfa;">${JSON.stringify(diff, null, 2)}</pre>
            `;
            debugFeed.appendChild(debugItem);
            debugFeed.scrollTop = debugFeed.scrollHeight;
            
        } catch(err) {
            console.error("Error parsing debug trace", err);
        }
    };
    debugSocket.onclose = () => {
        setTimeout(connectDebugSocket, 5000);
    };
};
connectDebugSocket();

