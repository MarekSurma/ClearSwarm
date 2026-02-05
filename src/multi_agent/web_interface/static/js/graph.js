// Interactive graph visualization using vis-network
let graphNetwork = null;
let graphNodes = null;
let graphEdges = null;
let graphUpdateInterval = null;
let currentGraphAgentId = null;

// Node details auto-refresh state
let selectedNodeId = null;
let selectedNodeIsRunning = false;
let nodeDetailsRefreshInterval = null;
let lastLogData = null;  // Cache for incremental updates

// Layout type management
const LAYOUT_STORAGE_KEY = 'agentGraphLayoutType';
const LAYOUT_TYPES = {
    PHYSICS: 'physics',
    HIERARCHICAL: 'hierarchical'
};

// Get current layout type from localStorage or default to physics
function getCurrentLayoutType() {
    return localStorage.getItem(LAYOUT_STORAGE_KEY) || LAYOUT_TYPES.PHYSICS;
}

// Set layout type and save to localStorage
function setLayoutType(layoutType) {
    localStorage.setItem(LAYOUT_STORAGE_KEY, layoutType);
}

// Get graph options based on layout type
function getGraphOptions(layoutType) {
    const baseOptions = {
        nodes: {
            font: {
                size: 14,
                color: '#e0c8a8',
                face: 'monospace'
            },
            borderWidth: 2,
            shadow: {
                enabled: true,
                color: 'rgba(180, 100, 50, 0.35)',
                size: 12,
                x: 0,
                y: 0
            }
        },
        edges: {
            width: 2,
            color: {
                color: '#5a3a28',
                highlight: '#8a6048',
                hover: '#8a6048'
            },
            arrows: {
                to: {
                    enabled: true,
                    scaleFactor: 0.5
                }
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 200,
            zoomView: true,
            dragView: true
        }
    };

    if (layoutType === LAYOUT_TYPES.HIERARCHICAL) {
        // Hierarchical layout
        return {
            ...baseOptions,
            edges: {
                ...baseOptions.edges,
                smooth: {
                    type: 'cubicBezier',
                    forceDirection: 'vertical',
                    roundness: 0.4
                }
            },
            layout: {
                hierarchical: {
                    enabled: true,
                    direction: 'UD',        // Up-Down
                    sortMethod: 'directed',
                    nodeSpacing: 150,
                    levelSeparation: 150,
                    shakeTowards: 'roots'
                }
            },
            physics: {
                enabled: true,
                hierarchicalRepulsion: {
                    centralGravity: 0.0,
                    springLength: 200,
                    springConstant: 0.01,
                    nodeDistance: 150,
                    damping: 0.09
                },
                solver: 'hierarchicalRepulsion'
            }
        };
    } else {
        // Physics-based layout with strong repulsion
        return {
            ...baseOptions,
            edges: {
                ...baseOptions.edges,
                smooth: {
                    type: 'continuous',
                    roundness: 0.5
                }
            },
            layout: {
                hierarchical: {
                    enabled: false
                }
            },
            physics: {
                enabled: true,
                barnesHut: {
                    gravitationalConstant: -10000,  // Very strong repulsion
                    centralGravity: 0.3,
                    springLength: 150,
                    springConstant: 0.04,
                    damping: 0.09,
                    avoidOverlap: 1  // Absolute no overlap
                },
                solver: 'barnesHut',
                stabilization: {
                    enabled: true,
                    iterations: 200,
                    updateInterval: 25
                }
            }
        };
    }
}

// Initialize graph visualization
function initializeGraph(agentId) {
    currentGraphAgentId = agentId;

    // Reset node details panel to empty state
    clearNodeLogs();

    // Create datasets
    graphNodes = new vis.DataSet([]);
    graphEdges = new vis.DataSet([]);

    // Get container
    const container = document.getElementById('graphContainer');

    // Clear container
    container.innerHTML = '';

    // Get current layout type
    const layoutType = getCurrentLayoutType();

    // Configure vis-network options based on layout type
    const options = getGraphOptions(layoutType);

    // Create network
    const data = {
        nodes: graphNodes,
        edges: graphEdges
    };

    graphNetwork = new vis.Network(container, data, options);

    // Add event listeners
    graphNetwork.on('click', function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            console.log('Clicked node:', nodeId);

            // Load and display node details
            loadNodeDetails(nodeId);
        } else {
            // Clicked on empty space - optionally clear selection
            // clearNodeLogs();
        }
    });

    graphNetwork.on('hoverNode', function(params) {
        container.style.cursor = 'pointer';
    });

    graphNetwork.on('blurNode', function(params) {
        container.style.cursor = 'default';
    });

    // Update layout button text to match current layout
    updateLayoutButtonText();

    // Load initial data
    loadGraphData();

    // Start auto-refresh
    startGraphAutoRefresh();
}

// Load graph data from API
async function loadGraphData() {
    if (!currentGraphAgentId) return;

    try {
        const response = await fetch(`${API_BASE}/api/executions/${currentGraphAgentId}/graph`);
        if (!response.ok) {
            throw new Error('Failed to load graph data');
        }

        const graphData = await response.json();

        // Update nodes
        const existingNodeIds = graphNodes.getIds();
        const newNodeIds = graphData.nodes.map(n => n.id);

        // Remove nodes that no longer exist
        const nodesToRemove = existingNodeIds.filter(id => !newNodeIds.includes(id));
        if (nodesToRemove.length > 0) {
            graphNodes.remove(nodesToRemove);
        }

        // Clear and rebuild the set of running node IDs
        runningNodeIds.clear();

        // Add or update nodes
        graphData.nodes.forEach(node => {
            // Track running nodes for animation
            if (node.is_running) {
                runningNodeIds.add(node.id);
            }
            // Determine border color based on state
            let borderColor = '#6b4030';  // Warm dark border for completed cells
            let borderWidth = 2;
            let shadowConfig = {
                enabled: true,
                color: 'rgba(180, 100, 50, 0.4)',
                size: 15,
                x: 0,
                y: 0
            };

            if (node.is_running) {
                // Get pulsating shadow size for animation
                const pulsatingShadowSize = getPulsatingShadowSize();

                // Color based on current state with pulsating shadow
                if (node.current_state === 'generating') {
                    borderColor = '#e89030';  // Warm amber - cell actively metabolizing
                    borderWidth = 4;
                    shadowConfig = {
                        enabled: true,
                        color: 'rgba(232, 144, 48, 0.7)',
                        size: pulsatingShadowSize,
                        x: 0,
                        y: 0
                    };
                } else if (node.current_state === 'waiting') {
                    borderColor = '#a06850';  // Warm muted rose - cell at rest
                    borderWidth = 4;
                    shadowConfig = {
                        enabled: true,
                        color: 'rgba(160, 104, 80, 0.6)',
                        size: pulsatingShadowSize,
                        x: 0,
                        y: 0
                    };
                } else if (node.current_state === 'executing_tool') {
                    borderColor = '#c89838';  // Warm golden - cell performing action
                    borderWidth = 4;
                    shadowConfig = {
                        enabled: true,
                        color: 'rgba(200, 152, 56, 0.7)',
                        size: pulsatingShadowSize,
                        x: 0,
                        y: 0
                    };
                } else {
                    borderColor = '#d0b880';  // Warm cream - generic active cell
                    borderWidth = 4;
                    shadowConfig = {
                        enabled: true,
                        color: 'rgba(208, 184, 128, 0.6)',
                        size: pulsatingShadowSize,
                        x: 0,
                        y: 0
                    };
                }
            }

            // Error styling - override border/shadow for nodes with errors
            if (node.error_count > 0 && !node.is_running) {
                borderColor = '#c03030';  // Crimson red border for error nodes
                borderWidth = 3;
                shadowConfig = {
                    enabled: true,
                    color: 'rgba(192, 48, 48, 0.6)',
                    size: 18,
                    x: 0,
                    y: 0
                };
            } else if (node.error_count > 0 && node.is_running) {
                // Running + errors: keep animation but tint red
                borderColor = '#d04030';  // Red-amber for running with errors
                shadowConfig.color = 'rgba(208, 64, 48, 0.7)';
            }

            // Enhanced label with state indicator for agents
            let enhancedLabel = node.label;
            if (node.is_running && node.current_state && node.group !== 'tool') {
                let stateIndicator = '';
                if (node.current_state === 'generating') {
                    stateIndicator = '⚡';  // Generating
                } else if (node.current_state === 'waiting') {
                    stateIndicator = '⏳';  // Waiting
                } else if (node.current_state === 'executing_tool') {
                    stateIndicator = '🔧';  // Executing tool
                }
                enhancedLabel = `${stateIndicator} ${node.label}`;
            }

            // Add error badge to label
            if (node.error_count > 0) {
                enhancedLabel = `⚠️ ${node.error_count}\n${enhancedLabel}`;
            }

            const visNode = {
                id: node.id,
                label: enhancedLabel,
                group: node.group,
                color: {
                    background: node.color,
                    border: borderColor,
                    highlight: {
                        background: node.color,
                        border: '#f0d8b0'
                    }
                },
                borderWidth: borderWidth,
                shadow: shadowConfig,
                shape: node.shape,
                size: node.size,
                title: createNodeTooltip(node)
            };

            if (graphNodes.get(node.id)) {
                graphNodes.update(visNode);
            } else {
                graphNodes.add(visNode);
            }
        });

        // Update edges
        const existingEdgeIds = graphEdges.getIds();
        const newEdgeIds = graphData.edges.map(e => e.id);

        // Remove edges that no longer exist
        const edgesToRemove = existingEdgeIds.filter(id => !newEdgeIds.includes(id));
        if (edgesToRemove.length > 0) {
            graphEdges.remove(edgesToRemove);
        }

        // Add or update edges
        graphData.edges.forEach(edge => {
            // Determine edge style based on call_mode
            const isAsync = edge.call_mode === 'asynchronous';

            const visEdge = {
                id: edge.id,
                from: edge.from_node,
                to: edge.to_node,
                dashes: isAsync,  // Dashed for async, solid for sync
                width: isAsync ? 2 : 3,  // Thinner for async
                color: {
                    color: isAsync ? '#7a5840' : '#5a3a28',  // Warmer tones for dark field
                    highlight: isAsync ? '#a07858' : '#8a6048'
                },
                title: `${edge.call_mode === 'asynchronous' ? 'Asynchronous' : 'Synchronous'} call`
            };

            if (graphEdges.get(edge.id)) {
                graphEdges.update(visEdge);
            } else {
                graphEdges.add(visEdge);
            }
        });

        // Update statistics
        updateGraphStats(graphData);

    } catch (error) {
        console.error('Failed to load graph data:', error);
    }
}

// Create tooltip for node
function createNodeTooltip(node) {
    // Get clean node name (remove state indicators)
    const nodeName = node.label.replace(/[⚡⏳🔧]\s*/g, '');
    if (node.error_count > 0) {
        return `${nodeName}\n⚠️ ${node.error_count} error${node.error_count > 1 ? 's' : ''}`;
    }
    return nodeName;
}

// Update graph statistics
function updateGraphStats(graphData) {
    const totalNodes = graphData.nodes.length;
    const agents = graphData.nodes.filter(n => n.group === 'agent' || n.group === 'root').length;
    const tools = graphData.nodes.filter(n => n.group === 'tool').length;
    const running = graphData.nodes.filter(n => n.is_running).length;
    const completed = graphData.nodes.filter(n => !n.is_running).length;
    const totalErrors = graphData.nodes.reduce((sum, n) => sum + (n.error_count || 0), 0);

    let errorsHtml = '';
    if (totalErrors > 0) {
        errorsHtml = `
            <div class="stat-item">
                <span class="stat-label">Errors:</span>
                <span class="stat-value status-error">${totalErrors}</span>
            </div>
        `;
    }

    const statsHtml = `
        <div class="graph-stats">
            <div class="stat-item">
                <span class="stat-label">Total Nodes:</span>
                <span class="stat-value">${totalNodes}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Agents:</span>
                <span class="stat-value">${agents}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Tools:</span>
                <span class="stat-value">${tools}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Running:</span>
                <span class="stat-value status-running">${running}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Completed:</span>
                <span class="stat-value status-completed">${completed}</span>
            </div>
            ${errorsHtml}
        </div>
    `;

    const statsContainer = document.getElementById('graphStats');
    if (statsContainer) {
        statsContainer.innerHTML = statsHtml;
    }
}

// Animation state for pulsating shadows
let animationPhase = 0;
let animationFrameCount = 0;

// Calculate pulsating shadow size based on animation phase
function getPulsatingShadowSize() {
    // Oscillate between 15 and 25
    return 20 + Math.sin(animationPhase) * 5;
}

// Update animation - called frequently for smooth animation
function updateGraphAnimation() {
    animationPhase += 0.15; // Increment for smooth animation
    animationFrameCount++;

    // Full data refresh only every 10 frames (1 second with 100ms interval)
    if (animationFrameCount >= 10) {
        animationFrameCount = 0;
        loadGraphData();
    } else {
        // Just update the shadow of running nodes for smooth animation
        updateRunningShadows();
    }
}

// Store which nodes are currently running for animation
let runningNodeIds = new Set();

// Update only shadows of running nodes for smooth animation
function updateRunningShadows() {
    if (!graphNodes || runningNodeIds.size === 0) return;

    const pulsatingShadowSize = getPulsatingShadowSize();

    runningNodeIds.forEach(nodeId => {
        const node = graphNodes.get(nodeId);
        if (node && node.shadow && typeof node.shadow.size === 'number' && node.shadow.size > 15) {
            // Update only the shadow property, preserving all other properties
            graphNodes.update({
                id: nodeId,
                shadow: {
                    enabled: node.shadow.enabled,
                    color: node.shadow.color,
                    size: pulsatingShadowSize,
                    x: node.shadow.x,
                    y: node.shadow.y
                }
            });
        }
    });
}

// Start auto-refresh for graph
function startGraphAutoRefresh() {
    stopGraphAutoRefresh(); // Clear any existing interval

    // Update every 100ms for smooth animation
    graphUpdateInterval = setInterval(() => {
        updateGraphAnimation();
    }, 100);
}

// Stop auto-refresh
function stopGraphAutoRefresh() {
    if (graphUpdateInterval) {
        clearInterval(graphUpdateInterval);
        graphUpdateInterval = null;
    }
}

// Cleanup graph when modal closes
function cleanupGraph() {
    stopGraphAutoRefresh();
    stopNodeDetailsRefresh();

    if (graphNetwork) {
        graphNetwork.destroy();
        graphNetwork = null;
    }

    graphNodes = null;
    graphEdges = null;
    currentGraphAgentId = null;

    // Reset animation state
    animationPhase = 0;
    animationFrameCount = 0;
    runningNodeIds.clear();

    // Reset node details state
    selectedNodeId = null;
    selectedNodeIsRunning = false;
    lastLogData = null;
}

// Graph control functions
function resetGraphPhysics() {
    if (graphNetwork) {
        graphNetwork.stabilize();
    }
}

function fitGraphView() {
    if (graphNetwork) {
        graphNetwork.fit({
            animation: {
                duration: 1000,
                easingFunction: 'easeInOutQuad'
            }
        });
    }
}

function toggleGraphPhysics() {
    if (graphNetwork) {
        const currentState = graphNetwork.physics.options.enabled;
        graphNetwork.setOptions({
            physics: {
                enabled: !currentState
            }
        });

        const btn = document.getElementById('togglePhysicsBtn');
        if (btn) {
            btn.textContent = currentState ? '▶️ Enable Physics' : '⏸️ Disable Physics';
        }
    }
}

// Export graph as image
function exportGraphImage() {
    if (graphNetwork) {
        const canvas = graphNetwork.canvas.frame.canvas;
        const dataURL = canvas.toDataURL('image/png');

        // Create download link
        const link = document.createElement('a');
        link.download = `agent-graph-${currentGraphAgentId}.png`;
        link.href = dataURL;
        link.click();
    }
}

// Load node details when clicked
async function loadNodeDetails(nodeId) {
    const logsContainer = document.getElementById('nodeLogs');

    // Stop previous refresh interval if selecting a different node
    if (selectedNodeId !== nodeId) {
        stopNodeDetailsRefresh();
        lastLogData = null;  // Clear cache for new node
    }

    // Store selected node
    selectedNodeId = nodeId;

    // Check if this is a tool or agent node
    const node = graphNodes.get(nodeId);
    const isToolNode = node && node.group === 'tool';
    selectedNodeIsRunning = node && runningNodeIds.has(nodeId);

    // Show loading state only on first load (no cached data)
    if (!lastLogData) {
        logsContainer.innerHTML = '<div class="node-logs-empty">Loading node details...</div>';
    }

    try {
        if (isToolNode) {
            // For tools, we need to extract the parent agent from the graph data
            await loadToolDetails(nodeId);
        } else {
            // For agents, load execution log
            await loadAgentDetails(nodeId);
        }

        // Start auto-refresh if node is running
        if (selectedNodeIsRunning && !nodeDetailsRefreshInterval) {
            startNodeDetailsRefresh();
        }

    } catch (error) {
        console.error('Failed to load node details:', error);
        logsContainer.innerHTML = `
            <div class="node-logs-empty" style="color: var(--danger-color);">
                Failed to load node details: ${error.message}
            </div>
        `;
    }
}

// Start auto-refresh for node details (every 1 second)
function startNodeDetailsRefresh() {
    stopNodeDetailsRefresh();  // Clear any existing interval

    nodeDetailsRefreshInterval = setInterval(async () => {
        if (!selectedNodeId) {
            stopNodeDetailsRefresh();
            return;
        }

        // Check if node is still running
        const node = graphNodes.get(selectedNodeId);
        const isStillRunning = node && runningNodeIds.has(selectedNodeId);

        if (!isStillRunning) {
            // Node completed - do one final refresh and stop
            await refreshNodeDetails();
            stopNodeDetailsRefresh();
            selectedNodeIsRunning = false;
            return;
        }

        await refreshNodeDetails();
    }, 1000);
}

// Stop node details auto-refresh
function stopNodeDetailsRefresh() {
    if (nodeDetailsRefreshInterval) {
        clearInterval(nodeDetailsRefreshInterval);
        nodeDetailsRefreshInterval = null;
    }
}

// Refresh node details without clearing the view
async function refreshNodeDetails() {
    if (!selectedNodeId) return;

    try {
        const node = graphNodes.get(selectedNodeId);
        const isToolNode = node && node.group === 'tool';

        if (isToolNode) {
            await loadToolDetails(selectedNodeId);
        } else {
            await loadAgentDetails(selectedNodeId);
        }
    } catch (error) {
        console.error('Failed to refresh node details:', error);
    }
}

// Load agent execution details
async function loadAgentDetails(agentId) {
    const response = await fetch(`${API_BASE}/api/executions/${agentId}/log`);

    if (!response.ok) {
        if (response.status === 404) {
            // Log not yet available - show "please wait..." instead of error
            const logsContainer = document.getElementById('nodeLogs');
            logsContainer.innerHTML = '<div class="node-logs-empty">Please wait...</div>';
            return;
        }
        throw new Error(`HTTP ${response.status}`);
    }

    const logData = await response.json();
    displayAgentLogs(logData);
}

// Load tool execution details
async function loadToolDetails(toolId) {
    // Find the tool in current graph data
    const edges = graphEdges.getIds();
    let parentAgentId = null;

    // Find parent agent by looking at edges
    for (const edgeId of edges) {
        const edge = graphEdges.get(edgeId);
        if (edge.to === toolId) {
            parentAgentId = edge.from;
            break;
        }
    }

    if (!parentAgentId) {
        throw new Error('Could not find parent agent for tool');
    }

    // Load parent agent's tools
    const response = await fetch(`${API_BASE}/api/executions/${parentAgentId}/tools`);

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }

    const tools = await response.json();
    const tool = tools.find(t => t.tool_execution_id === toolId);

    if (!tool) {
        throw new Error('Tool not found');
    }

    displayToolLogs(tool);
}

// Display agent logs in the panel
function displayAgentLogs(logData) {
    const logsContainer = document.getElementById('nodeLogs');

    // Extract messages from log data for comparison
    const newMessages = extractMessagesFromLog(logData);
    const previousMessageCount = lastLogData ? extractMessagesFromLog(lastLogData).length : 0;

    // Check if we can do incremental update (same agent, more messages)
    const canIncrementalUpdate = lastLogData &&
        lastLogData.agent_id === logData.agent_id &&
        newMessages.length > previousMessageCount;

    // Update cache
    lastLogData = logData;

    // If incremental update is possible, only append new messages
    if (canIncrementalUpdate) {
        const conversationContainer = logsContainer.querySelector('.node-log-conversation');
        if (conversationContainer) {
            // Update header with new message count
            const headerLabel = logsContainer.querySelector('.node-log-section:nth-child(2) .node-log-label');
            if (headerLabel) {
                headerLabel.textContent = `Conversation Context (${newMessages.length} messages)`;
            }

            // Update status badge
            const statusBadge = logsContainer.querySelector('.node-log-badge');
            if (statusBadge) {
                if (logData.session_ended_explicitly !== null) {
                    statusBadge.className = 'node-log-badge completed';
                    statusBadge.textContent = '✓ Completed';
                } else {
                    statusBadge.className = 'node-log-badge running';
                    statusBadge.textContent = '⟳ Running';
                }
            }

            // Update iterations count
            const iterationsDiv = logsContainer.querySelector('.node-log-section .node-log-value');
            if (iterationsDiv) {
                iterationsDiv.innerHTML = `${logData.agent_id.substring(0, 12)}... • ${logData.total_iterations || 0} iterations`;
            }

            // Append only new messages
            const newMessagesToAdd = newMessages.slice(previousMessageCount);
            newMessagesToAdd.forEach((msg, idx) => {
                const globalIdx = previousMessageCount + idx;
                const messageHtml = createMessageHtml(msg, globalIdx);
                conversationContainer.insertAdjacentHTML('beforeend', messageHtml);
            });

            // Scroll to bottom
            scrollNodeLogsToBottom();
            return;
        }
    }

    // Full render (first load or structure changed)
    const statusBadge = logData.session_ended_explicitly !== null
        ? `<span class="node-log-badge completed">✓ Completed</span>`
        : `<span class="node-log-badge running">⟳ Running</span>`;

    let html = `
        <div class="node-log-section">
            <div class="node-log-label">${logData.agent_name}${statusBadge}</div>
            <div class="node-log-value" style="font-size: 0.75rem; color: var(--text-muted);">
                ${logData.agent_id.substring(0, 12)}... • ${logData.total_iterations || 0} iterations
            </div>
        </div>
    `;

    // Display full conversation context
    if (newMessages.length > 0) {
        html += `
            <div class="node-log-section">
                <div class="node-log-label">Conversation Context (${newMessages.length} messages)</div>
                <div class="node-log-conversation">
        `;

        // Show all messages
        newMessages.forEach((msg, idx) => {
            html += createMessageHtml(msg, idx);
        });

        html += `
                </div>
            </div>
        `;
    } else {
        html += `
            <div class="node-log-section">
                <div style="color: var(--text-muted); font-style: italic; text-align: center; padding: 20px;">
                    No conversation context available
                </div>
            </div>
        `;
    }

    logsContainer.innerHTML = html;

    // Scroll to bottom after full render
    scrollNodeLogsToBottom();
}

// Extract messages from log data
function extractMessagesFromLog(logData) {
    // New simplified format: interactions IS the flat array of messages
    // Each message has {role, content} and optionally {timestamp}
    if (!logData.interactions || logData.interactions.length === 0) {
        return [];
    }

    // interactions is already a flat array of messages - just return it
    return logData.interactions;
}

// Create HTML for a single message
function createMessageHtml(msg, idx) {
    const role = msg.role || 'unknown';
    const content = msg.content || '';

    // Determine message styling based on role
    let roleClass = 'conversation-role-other';
    let roleIcon = '💬';
    let roleColor = '#94a3b8';

    if (role === 'user') {
        roleClass = 'conversation-role-user';
        roleIcon = '👤';
        roleColor = '#3b82f6';
    } else if (role === 'assistant') {
        roleClass = 'conversation-role-assistant';
        roleIcon = '🤖';
        roleColor = '#10b981';
    } else if (role === 'system') {
        roleClass = 'conversation-role-system';
        roleIcon = '⚙️';
        roleColor = '#f59e0b';
    } else if (role === 'tool') {
        roleClass = 'conversation-role-tool';
        roleIcon = '🔧';
        roleColor = '#8b5cf6';
    }

    return `
        <div class="conversation-message ${roleClass}">
            <div class="conversation-header">
                <span style="color: ${roleColor};">${roleIcon} ${role}</span>
                <span class="conversation-index">#${idx + 1}</span>
            </div>
            <div class="conversation-content">${escapeHtml(content)}</div>
        </div>
    `;
}

// Scroll node logs container to bottom
function scrollNodeLogsToBottom() {
    const logsContainer = document.getElementById('nodeLogs');
    if (logsContainer) {
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }
}

// Display tool logs in the panel
function displayToolLogs(tool) {
    const logsContainer = document.getElementById('nodeLogs');

    const statusBadge = tool.is_running
        ? `<span class="node-log-badge running">⟳ Running</span>`
        : `<span class="node-log-badge completed">✓ Completed</span>`;

    const callModeBadge = tool.call_mode === 'asynchronous'
        ? '<span style="color: var(--text-muted); font-size: 0.75rem;">(Async)</span>'
        : '<span style="color: var(--text-muted); font-size: 0.75rem;">(Sync)</span>';

    let html = `
        <div class="node-log-section">
            <div class="node-log-label">Tool: ${tool.tool_name}${statusBadge}</div>
            <div class="node-log-value">ID: <code>${tool.tool_execution_id}</code></div>
            <div class="node-log-value">Mode: ${callModeBadge}</div>
        </div>

        <div class="node-log-section">
            <div class="node-log-label">Execution Time</div>
            <div class="node-log-value">Started: ${new Date(tool.started_at).toLocaleString()}</div>
            ${tool.completed_at ? `<div class="node-log-value">Completed: ${new Date(tool.completed_at).toLocaleString()}</div>` : ''}
        </div>

        <div class="node-log-section">
            <div class="node-log-label">Parameters</div>
            <div class="node-log-interactions">
                <pre style="margin: 0; white-space: pre-wrap;">${JSON.stringify(tool.parameters, null, 2)}</pre>
            </div>
        </div>
    `;

    if (tool.result) {
        html += `
            <div class="node-log-section">
                <div class="node-log-label">Result</div>
                <div class="node-log-interactions">
                    ${escapeHtml(tool.result)}
                </div>
            </div>
        `;
    }

    logsContainer.innerHTML = html;
}

// Clear node logs
function clearNodeLogs() {
    // Stop auto-refresh
    stopNodeDetailsRefresh();

    // Clear state
    selectedNodeId = null;
    selectedNodeIsRunning = false;
    lastLogData = null;

    const logsContainer = document.getElementById('nodeLogs');
    logsContainer.innerHTML = `
        <div class="node-logs-empty">
            Click on any node in the graph to view its execution details
        </div>
    `;
}

// Helper: Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Toggle system message collapse/expand
function toggleSystemMessage(messageId) {
    const content = document.getElementById(`${messageId}-content`);
    const toggle = document.getElementById(`${messageId}-toggle`);
    const preview = document.getElementById(`${messageId}-preview`);

    if (!content || !toggle) return;

    const isExpanded = content.classList.contains('expanded');

    if (isExpanded) {
        // Collapse
        content.classList.remove('expanded');
        toggle.classList.remove('expanded');
        toggle.querySelector('.toggle-text').textContent = 'Show';
        if (preview) preview.classList.remove('hidden');
    } else {
        // Expand
        content.classList.add('expanded');
        toggle.classList.add('expanded');
        toggle.querySelector('.toggle-text').textContent = 'Hide';
        if (preview) preview.classList.add('hidden');
    }
}

// Stop all agents in the current execution tree
async function stopCurrentExecutionTree() {
    if (!currentGraphAgentId) {
        console.error('No current graph agent ID');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/agents/stop/${currentGraphAgentId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Failed to stop agents');
        }

        const result = await response.json();

        // Show status message using the main.js function if available
        if (typeof showLaunchStatus === 'function') {
            showLaunchStatus(result.message, 'success');
        }

        // Reload graph data to reflect changes
        await loadGraphData();

        // Also reload main executions list if function exists
        if (typeof loadExecutions === 'function') {
            await loadExecutions();
        }

    } catch (error) {
        console.error('Failed to stop agents:', error);
        if (typeof showLaunchStatus === 'function') {
            showLaunchStatus('Failed to stop agents: ' + error.message, 'error');
        }
    }
}

// Switch graph layout type
function switchGraphLayout(newLayoutType) {
    if (!graphNetwork) return;

    // Save new layout type
    setLayoutType(newLayoutType);

    // Get new options
    const newOptions = getGraphOptions(newLayoutType);

    // Apply new options to existing network
    graphNetwork.setOptions(newOptions);

    // Update button text
    updateLayoutButtonText();

    // Stabilize after layout change
    setTimeout(() => {
        graphNetwork.stabilize();
        graphNetwork.fit();
    }, 100);
}

// Update layout button text based on current layout
function updateLayoutButtonText() {
    const btn = document.getElementById('toggleLayoutBtn');
    if (!btn) return;

    const currentLayout = getCurrentLayoutType();
    if (currentLayout === LAYOUT_TYPES.HIERARCHICAL) {
        btn.innerHTML = '🌳 Hierarchical';
    } else {
        btn.innerHTML = '🌀 Physics';
    }
}

// Toggle between layout types (called from HTML button)
function toggleLayoutType() {
    const currentLayout = getCurrentLayoutType();
    const newLayout = currentLayout === LAYOUT_TYPES.PHYSICS
        ? LAYOUT_TYPES.HIERARCHICAL
        : LAYOUT_TYPES.PHYSICS;

    switchGraphLayout(newLayout);
}
