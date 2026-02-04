// WebSocket connection for real-time updates

let ws = null;
let reconnectInterval = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;

// Initialize WebSocket connection
function initializeWebSocket() {
    connectWebSocket();
}

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/updates`;

    console.log('Connecting to WebSocket:', wsUrl);

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WebSocket connected');
            reconnectAttempts = 0;
            updateConnectionStatus(true);

            // Clear reconnect interval if exists
            if (reconnectInterval) {
                clearInterval(reconnectInterval);
                reconnectInterval = null;
            }

            // Send periodic pings to keep connection alive
            setInterval(() => {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send('ping');
                }
            }, 30000); // Every 30 seconds
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(message);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateConnectionStatus(false);
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected');
            updateConnectionStatus(false);

            // Attempt to reconnect
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                reconnectAttempts++;
                const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
                console.log(`Reconnecting in ${delay}ms... (attempt ${reconnectAttempts})`);

                setTimeout(() => {
                    connectWebSocket();
                }, delay);
            } else {
                console.error('Max reconnect attempts reached');
            }
        };

    } catch (error) {
        console.error('Failed to create WebSocket:', error);
        updateConnectionStatus(false);
    }
}

// Handle WebSocket messages
function handleWebSocketMessage(message) {
    console.log('WebSocket message:', message);

    switch (message.type) {
        case 'initial_state':
            console.log('Received initial state:', message.executions.length, 'executions');
            // Initial state received, executions are already loaded via REST API
            break;

        case 'executions_update':
            console.log('Executions updated:', message.executions.length);
            // Update executions list
            executions = message.executions;
            renderExecutions();
            break;

        case 'running_agents':
            console.log('Running agents:', message.count);
            // Update running count
            document.getElementById('runningAgents').innerHTML =
                `Running: <strong>${message.count}</strong>`;

            // If auto-refresh is off, still update the data
            if (!autoRefresh) {
                executions = executions.map(exec => {
                    const runningAgent = message.agents.find(a => a.agent_id === exec.agent_id);
                    if (runningAgent) {
                        return {
                            ...exec,
                            current_state: runningAgent.current_state,
                            is_running: true
                        };
                    }
                    return exec;
                });
                renderExecutions();
            }
            break;

        case 'agent_state':
            console.log('Agent state:', message.agent_id);
            break;

        case 'agent_update':
            console.log('Agent update:', message.agent_id);
            // Refresh executions if auto-refresh is on
            if (autoRefresh) {
                loadExecutions();
            }
            break;

        case 'agent_completed':
            console.log('Agent completed:', message.agent_id);
            // Refresh executions
            loadExecutions();
            break;

        default:
            console.log('Unknown message type:', message.type);
    }
}

// Update connection status indicator
function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connectionStatus');
    const dot = statusElement.querySelector('.dot');

    if (connected) {
        statusElement.innerHTML = '<span class="dot online"></span> Connected';
    } else {
        statusElement.innerHTML = '<span class="dot offline"></span> Disconnected';
    }
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (ws) {
        ws.close();
    }
    if (reconnectInterval) {
        clearInterval(reconnectInterval);
    }
});
