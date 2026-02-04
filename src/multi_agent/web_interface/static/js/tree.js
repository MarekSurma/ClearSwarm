// Tree visualization logic

// Render execution tree
function renderTree(node, indent = '', isLast = true) {
    let html = '<div class="tree-content">';
    html += renderNode(node, indent, isLast);
    html += '</div>';
    return html;
}

function renderNode(node, indent = '', isLast = true) {
    let output = '';

    // Tree connectors
    const connector = isLast ? '└─ ' : '├─ ';
    const prefix = indent + connector;

    // Status indicator
    const statusIcon = node.is_running ? '⟳' : '✓';
    const statusClass = node.is_running ? 'running' : 'completed';

    // Duration
    let duration = '';
    if (node.completed_at) {
        duration = ` (${calculateDuration(node.started_at, node.completed_at)})`;
    } else {
        duration = ' (running...)';
    }

    // Agent line
    output += `<div class="tree-node agent ${statusClass}">`;
    output += `${prefix}${statusIcon} <strong>${node.agent_name}</strong> [${node.agent_id.substring(0, 8)}]${duration}`;
    output += `</div>\n`;

    // Update indent for children
    const childIndent = indent + (isLast ? '   ' : '│  ');

    // Render tools
    if (node.tools && node.tools.length > 0) {
        node.tools.forEach((tool, index) => {
            const isLastTool = index === node.tools.length - 1 && (!node.children || node.children.length === 0);
            const toolConnector = isLastTool ? '└─ ' : '├─ ';
            const toolStatus = tool.is_running ? '⟳' : '✓';
            const toolClass = tool.is_running ? 'running' : 'completed';

            let toolDuration = '';
            if (tool.completed_at) {
                toolDuration = ` (${calculateDuration(tool.started_at, tool.completed_at)})`;
            } else {
                toolDuration = ' (running...)';
            }

            output += `<div class="tree-node tool ${toolClass}">`;
            output += `${childIndent}${toolConnector}🔧 ${tool.tool_name}${toolDuration}`;

            // Show parameters (abbreviated)
            const paramsStr = JSON.stringify(tool.parameters);
            if (paramsStr.length > 50) {
                output += ` <span style="color: var(--text-muted)">${paramsStr.substring(0, 50)}...</span>`;
            } else {
                output += ` <span style="color: var(--text-muted)">${paramsStr}</span>`;
            }

            output += `</div>\n`;
        });
    }

    // Render child agents
    if (node.children && node.children.length > 0) {
        node.children.forEach((child, index) => {
            const isLastChild = index === node.children.length - 1;
            output += renderNode(child, childIndent, isLastChild);
        });
    }

    return output;
}

// Helper function to calculate duration (reused from main.js)
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
