const cliInput = document.getElementById('cli-input');
const chatHistory = document.getElementById('chat-history');
const terminalFeed = document.getElementById('terminal-feed');
const workspaces = document.querySelectorAll('.workspace');
const canvasToggle = document.getElementById('canvas-toggle');
const contextContent = document.getElementById('context-content');
const canvasIframe = document.getElementById('canvas-iframe');

let currentWorkspace = 1;
let canvasMode = false;

// Quick commands
const handleQuickCommand = (cmd) => {
    switch(cmd.trim()) {
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

// Workspace switching via Alt+1 to Alt+0
window.addEventListener('keydown', (e) => {
    if (e.altKey && e.key >= '0' && e.key <= '9') {
        e.preventDefault();
        const wsNum = e.key === '0' ? 10 : parseInt(e.key);
        workspaces.forEach(w => w.classList.remove('active'));
        document.querySelector(`[data-ws="${wsNum}"]`).classList.add('active');
        currentWorkspace = wsNum;
        document.getElementById('status').innerHTML = `Agentic OS - Workspace ${wsNum} <button id="canvas-toggle">[Toggle Canvas]</button>`;
        appendChat(`Switched to Workspace ${wsNum}`, 'system');
        bindCanvasToggle();
    }
});

const bindCanvasToggle = () => {
    document.getElementById('canvas-toggle').addEventListener('click', () => {
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
document.addEventListener('click', () => cliInput.focus());
cliInput.focus();
