// Main application logic
const API_BASE = '';

// State
let agents = [];
let executions = [];
let autoRefreshInterval = null;

// Initialize application
document.addEventListener('DOMContentLoaded', async () => {
    await loadAgents();
    await loadExecutions();
    setupEventListeners();
    initializeWebSocket();
    startAutoRefresh();
});

// Setup event listeners
function setupEventListeners() {
    // Agent selection
    document.getElementById('agentSelect').addEventListener('change', (e) => {
        const selectedAgent = agents.find(a => a.name === e.target.value);
        const descElement = document.getElementById('agentDescription');
        if (selectedAgent) {
            descElement.textContent = selectedAgent.description;
        } else {
            descElement.textContent = '';
        }
    });

    // Launch form
    document.getElementById('launchForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await launchAgent();
    });

    // Stop All button
    document.getElementById('stopAllBtn').addEventListener('click', async () => {
        await stopAllAgents();
    });

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            switchTab(btn.dataset.tab);
        });
    });

    // Close modal
    document.getElementById('closeModalBtn').addEventListener('click', () => {
        closeModal();
    });

    // Close details
    document.getElementById('closeDetailsBtn').addEventListener('click', () => {
        document.getElementById('executionDetails').style.display = 'none';
    });
}

// Load agents from API
async function loadAgents() {
    try {
        const response = await fetch(`${API_BASE}/api/agents`);
        agents = await response.json();

        // Populate select
        const select = document.getElementById('agentSelect');
        select.innerHTML = '<option value="">-- Select an agent --</option>';
        agents.forEach(agent => {
            const option = document.createElement('option');
            option.value = agent.name;
            option.textContent = agent.name;
            select.appendChild(option);
        });

        // Populate agents list
        renderAgentsList();

    } catch (error) {
        console.error('Failed to load agents:', error);
        showLaunchStatus('Failed to load agents', 'error');
    }
}

// Render agents list
function renderAgentsList() {
    const container = document.getElementById('agentsList');

    if (agents.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted)">No agents available</p>';
        return;
    }

    container.innerHTML = agents.map(agent => `
        <div class="agent-card">
            <div class="agent-card-name">${agent.name}</div>
            <div class="agent-card-desc">${agent.description}</div>
        </div>
    `).join('');
}

// Launch agent
async function launchAgent() {
    const agentName = document.getElementById('agentSelect').value;
    const message = document.getElementById('messageInput').value;

    if (!agentName || !message) {
        showLaunchStatus('Please select an agent and enter a message', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/agents/run`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                agent_name: agentName,
                message: message
            })
        });

        if (!response.ok) {
            throw new Error('Failed to launch agent');
        }

        const result = await response.json();
        showLaunchStatus(`Agent launched successfully! ID: ${result.agent_id}`, 'success');

        // Clear form
        document.getElementById('messageInput').value = '';

        // Reload executions after a short delay
        setTimeout(() => loadExecutions(), 1000);

    } catch (error) {
        console.error('Failed to launch agent:', error);
        showLaunchStatus('Failed to launch agent', 'error');
    }
}

// Show launch status message using toast notifications
function showLaunchStatus(message, type) {
    // Use toast notifications for better UX
    if (type === 'success') {
        toastSuccess(message, { title: 'Agent Launched' });
    } else if (type === 'error') {
        toastError(message);
    } else {
        toastInfo(message);
    }
}

// Load executions from API
async function loadExecutions() {
    try {
        const response = await fetch(`${API_BASE}/api/executions`);
        executions = await response.json();

        renderExecutions();

    } catch (error) {
        console.error('Failed to load executions:', error);
    }
}

// Render executions in all tabs
function renderExecutions() {
    // Root executions
    const rootExecs = executions.filter(e => e.parent_agent_id === null);
    renderExecutionsList('rootExecutionsList', rootExecs);

    // All executions
    renderExecutionsList('allExecutionsList', executions);

    // Running executions
    const runningExecs = executions.filter(e => e.is_running);
    renderExecutionsList('runningExecutionsList', runningExecs);

    // Update running count
    document.getElementById('runningAgents').innerHTML =
        `Running: <strong>${runningExecs.length}</strong>`;
}

// Render executions list
function renderExecutionsList(containerId, execs) {
    const container = document.getElementById(containerId);

    if (execs.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted)">No executions found</p>';
        return;
    }

    container.innerHTML = execs.map(exec => {
        const statusClass = exec.is_running ? 'running' : 'completed';
        const statusText = exec.is_running ? 'Running' : 'Completed';
        const startedAt = new Date(exec.started_at).toLocaleString();
        const duration = exec.completed_at
            ? calculateDuration(exec.started_at, exec.completed_at)
            : 'Running...';

        return `
            <div class="execution-card ${statusClass}" data-id="${exec.agent_id}">
                <div class="execution-header">
                    <div class="execution-name">
                        ${exec.agent_name}
                        ${exec.parent_agent_id ? `<span style="color: var(--text-muted); font-size: 0.85rem;">← ${exec.parent_agent_name}</span>` : ''}
                    </div>
                    <div class="execution-status ${statusClass}">${statusText}</div>
                </div>
                <div class="execution-info">
                    <div>⏰ ${startedAt}</div>
                    <div>⏱️ ${duration}</div>
                    <div>🆔 ${exec.agent_id.substring(0, 8)}...</div>
                </div>
                <div class="execution-actions">
                    <button class="action-btn" onclick="viewExecutionTree('${exec.agent_id}')">
                        🌳 View Tree
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Calculate duration between two timestamps
function calculateDuration(start, end) {
    const startTime = new Date(start);
    const endTime = new Date(end);
    const diffMs = endTime - startTime;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);

    if (diffHour > 0) {
        return `${diffHour}h ${diffMin % 60}m`;
    } else if (diffMin > 0) {
        return `${diffMin}m ${diffSec % 60}s`;
    } else {
        return `${diffSec}s`;
    }
}

// View execution tree (now opens interactive graph)
async function viewExecutionTree(agentId) {
    try {
        // Open graph modal
        document.getElementById('graphModal').classList.add('active');

        // Initialize graph visualization
        initializeGraph(agentId);

    } catch (error) {
        console.error('Failed to load execution graph:', error);
        toastError('Failed to load execution graph');
    }
}

// View execution details
async function viewExecutionDetails(agentId) {
    try {
        const [execResponse, toolsResponse] = await Promise.all([
            fetch(`${API_BASE}/api/executions/${agentId}`),
            fetch(`${API_BASE}/api/executions/${agentId}/tools`)
        ]);

        const exec = await execResponse.json();
        const tools = await toolsResponse.json();

        const detailsHtml = `
            <div class="detail-section">
                <h3>Agent Information</h3>
                <div class="detail-grid">
                    <div class="detail-label">Agent Name:</div>
                    <div class="detail-value">${exec.agent_name}</div>

                    <div class="detail-label">Agent ID:</div>
                    <div class="detail-value">${exec.agent_id}</div>

                    <div class="detail-label">Parent:</div>
                    <div class="detail-value">${exec.parent_agent_name}</div>

                    <div class="detail-label">Status:</div>
                    <div class="detail-value">
                        <span class="execution-status ${exec.is_running ? 'running' : 'completed'}">
                            ${exec.is_running ? 'Running' : 'Completed'}
                        </span>
                    </div>

                    <div class="detail-label">Current State:</div>
                    <div class="detail-value">${exec.current_state}</div>

                    <div class="detail-label">Call Mode:</div>
                    <div class="detail-value">${exec.call_mode}</div>

                    <div class="detail-label">Started:</div>
                    <div class="detail-value">${new Date(exec.started_at).toLocaleString()}</div>

                    <div class="detail-label">Completed:</div>
                    <div class="detail-value">${exec.completed_at ? new Date(exec.completed_at).toLocaleString() : 'Still running...'}</div>
                </div>
            </div>

            <div class="detail-section">
                <h3>Tool Executions (${tools.length})</h3>
                ${tools.length === 0 ? '<p style="color: var(--text-muted)">No tools executed yet</p>' :
                    tools.map(tool => `
                        <div class="tool-execution ${tool.is_running ? 'running' : ''}">
                            <div class="tool-header">
                                <div class="tool-name">${tool.tool_name}</div>
                                <div class="execution-status ${tool.is_running ? 'running' : 'completed'}">
                                    ${tool.is_running ? 'Running' : 'Completed'}
                                </div>
                            </div>
                            <div class="tool-params">
                                <strong>Parameters:</strong> ${JSON.stringify(tool.parameters)}
                            </div>
                            <div class="tool-params">
                                <strong>Mode:</strong> ${tool.call_mode}
                            </div>
                            ${tool.result ? `
                                <div class="tool-result">
                                    <strong>Result:</strong><br>
                                    ${escapeHtml(tool.result.substring(0, 500))}${tool.result.length > 500 ? '...' : ''}
                                </div>
                            ` : ''}
                        </div>
                    `).join('')
                }
            </div>
        `;

        document.getElementById('executionDetailsContent').innerHTML = detailsHtml;
        document.getElementById('executionDetails').style.display = 'block';

    } catch (error) {
        console.error('Failed to load execution details:', error);
        toastError('Failed to load execution details');
    }
}

// View execution log
async function viewExecutionLog(agentId) {
    try {
        // First get execution info to retrieve log_file name
        const execResponse = await fetch(`${API_BASE}/api/executions/${agentId}`);
        const execInfo = await execResponse.json();

        const response = await fetch(`${API_BASE}/api/executions/${agentId}/log`);
        const log = await response.json();

        // Extract filename from log_file path or use default
        let filename = `agent_${agentId}.log`;
        if (execInfo.log_file) {
            const parts = execInfo.log_file.split('/');
            filename = parts[parts.length - 1];
        }

        // Open in new window or download
        const logJson = JSON.stringify(log, null, 2);
        const blob = new Blob([logJson], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);

    } catch (error) {
        console.error('Failed to load execution log:', error);
        toastError('Failed to load execution log');
    }
}

// Stop all running agents
async function stopAllAgents() {
    const btn = document.getElementById('stopAllBtn');
    const originalText = btn.textContent;

    try {
        btn.textContent = 'Stopping...';
        btn.disabled = true;

        const response = await fetch(`${API_BASE}/api/agents/stop-all`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Failed to stop agents');
        }

        const result = await response.json();

        // Show status message
        showLaunchStatus(result.message, 'success');

        // Reload executions to reflect changes
        await loadExecutions();

    } catch (error) {
        console.error('Failed to stop agents:', error);
        showLaunchStatus('Failed to stop agents', 'error');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// Start auto-refresh (always enabled)
function startAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    autoRefreshInterval = setInterval(() => {
        loadExecutions();
    }, 3000); // Refresh every 3 seconds
}

// Switch tabs
function switchTab(tabName) {
    // Update buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}Tab`).classList.add('active');
}

// Close modal
function closeModal() {
    document.getElementById('treeModal').classList.remove('active');
}

// Close graph modal
function closeGraphModal() {
    const modal = document.getElementById('graphModal');
    if (modal) {
        modal.classList.remove('active');
        // Cleanup graph resources
        if (typeof cleanupGraph === 'function') {
            cleanupGraph();
        }
    }
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Close modal on outside click
document.getElementById('treeModal').addEventListener('click', (e) => {
    if (e.target.id === 'treeModal') {
        closeModal();
    }
});

// Close graph modal on outside click
document.addEventListener('DOMContentLoaded', () => {
    const graphModal = document.getElementById('graphModal');
    if (graphModal) {
        graphModal.addEventListener('click', (e) => {
            if (e.target.id === 'graphModal') {
                closeGraphModal();
            }
        });
    }
});
