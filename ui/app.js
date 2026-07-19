const cliInput = document.getElementById('cli-input');
const chatHistory = document.getElementById('chat-history');
const terminalFeed = document.getElementById('terminal-feed');
const workspacesContainer = document.getElementById('workspaces');
const addWorkspaceBtn = document.getElementById('add-workspace-btn');
const canvasToggle = document.getElementById('canvas-toggle');
const contextContent = document.getElementById('context-content');
const canvasIframe = document.getElementById('canvas-iframe');

let currentWorkspace = 1;
let totalWorkspaces = 1;
let canvasMode = false;

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
            // Send to WebSocket
            if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
                chatSocket.send(val);
            } else {
                appendChat('WebSocket not connected.', 'system');
            }
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
                const text = parsed.action || parsed.message || JSON.stringify(parsed);
                appendChat(text, item.status === 'USER_INPUT' ? 'user' : 'agent');
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
    document.getElementById('status').innerHTML = `Agentic OS - Workspace ${wsNum} <button id="canvas-toggle">[Toggle Canvas]</button>`;
    loadWorkspaceHistory(wsNum);
    bindCanvasToggle();
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

const bindCanvasToggle = () => {
    const toggleBtn = document.getElementById('canvas-toggle');
    if (!toggleBtn) return;
    toggleBtn.addEventListener('click', () => {
        canvasMode = !canvasMode;
        if (canvasMode) {
            contextContent.style.display = 'none';
            canvasIframe.style.display = 'block';
            canvasIframe.src = "http://localhost:8000/ui/index.html"; // Just a mock target to test iframe
            appendChat('Toggled Canvas Mode ON', 'system');
        } else {
            contextContent.style.display = 'block';
            canvasIframe.style.display = 'none';
            canvasIframe.src = "";
            appendChat('Toggled Canvas Mode OFF', 'system');
        }
    });
};
bindCanvasToggle();

// WebSockets
let notifSocket, chatSocket;

const connectSockets = () => {
    notifSocket = new WebSocket(`ws://${location.host}/api/v1/stream/notifications`);
    notifSocket.onmessage = (e) => {
        const data = JSON.parse(e.data);
        appendLog(data.level || 'info', data.message);
    };

    chatSocket = new WebSocket(`ws://${location.host}/api/v1/stream/chat`);
    chatSocket.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.status === 'REQUIRES_CLARIFICATION') {
            appendChat(data.message, 'system');
        } else {
            appendChat(data.action || data.message, 'agent');
        }
    };
};

connectSockets();

// Always focus input
document.addEventListener('click', (e) => {
    // Don't focus if they clicked a button or resizer
    if (e.target.tagName !== 'BUTTON' && !e.target.classList.contains('resizer') && !e.target.classList.contains('workspace')) {
        cliInput.focus();
    }
});
cliInput.focus();
loadWorkspaceHistory(currentWorkspace);
