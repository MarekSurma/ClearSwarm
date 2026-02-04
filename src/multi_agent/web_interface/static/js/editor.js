/**
 * Agent Editor JavaScript
 */

// State
let currentAgent = null;
let isNewAgent = false;
let allAgents = [];
let allTools = [];

// DOM Elements
const agentsList = document.getElementById('agentsList');
const editorTitle = document.getElementById('editorTitle');
const editorActions = document.getElementById('editorActions');
const editorPlaceholder = document.getElementById('editorPlaceholder');
const agentForm = document.getElementById('agentForm');
const agentNameInput = document.getElementById('agentName');
const agentDescriptionInput = document.getElementById('agentDescription');
const agentSystemPromptInput = document.getElementById('agentSystemPrompt');
const toolsCheckboxes = document.getElementById('toolsCheckboxes');
const agentsCheckboxes = document.getElementById('agentsCheckboxes');
const newAgentBtn = document.getElementById('newAgentBtn');
const deleteAgentBtn = document.getElementById('deleteAgentBtn');
const cancelBtn = document.getElementById('cancelBtn');
const deleteModal = document.getElementById('deleteModal');
const deleteAgentName = document.getElementById('deleteAgentName');
const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadAgents();
    loadTools();
    setupEventListeners();
});

function setupEventListeners() {
    newAgentBtn.addEventListener('click', showNewAgentForm);
    cancelBtn.addEventListener('click', hideForm);
    agentForm.addEventListener('submit', handleFormSubmit);
    deleteAgentBtn.addEventListener('click', showDeleteModal);
    cancelDeleteBtn.addEventListener('click', hideDeleteModal);
    confirmDeleteBtn.addEventListener('click', handleDelete);
}

// API Functions
async function loadAgents() {
    try {
        const response = await fetch('/api/agents');
        allAgents = await response.json();
        renderAgentsList();
        renderAgentsCheckboxes();
    } catch (error) {
        console.error('Failed to load agents:', error);
        agentsList.innerHTML = '<p class="text-muted">Failed to load agents</p>';
    }
}

async function loadTools() {
    try {
        const response = await fetch('/api/tools');
        allTools = await response.json();
        renderToolsCheckboxes();
    } catch (error) {
        console.error('Failed to load tools:', error);
        toolsCheckboxes.innerHTML = '<p class="text-muted">Failed to load tools</p>';
    }
}

async function loadAgentDetail(agentName) {
    try {
        const response = await fetch(`/api/agents/${agentName}/detail`);
        if (!response.ok) throw new Error('Agent not found');
        return await response.json();
    } catch (error) {
        console.error('Failed to load agent detail:', error);
        return null;
    }
}

// Render Functions
function renderAgentsList() {
    if (allAgents.length === 0) {
        agentsList.innerHTML = '<p class="text-muted">No agents found</p>';
        return;
    }

    agentsList.innerHTML = allAgents.map(agent => `
        <div class="editor-agent-item ${currentAgent?.name === agent.name ? 'active' : ''}"
             data-agent="${agent.name}">
            <div class="editor-agent-item-name">${agent.name}</div>
            <div class="editor-agent-item-desc">${agent.description}</div>
        </div>
    `).join('');

    // Add click handlers
    document.querySelectorAll('.editor-agent-item').forEach(item => {
        item.addEventListener('click', () => selectAgent(item.dataset.agent));
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderToolsCheckboxes() {
    if (allTools.length === 0) {
        toolsCheckboxes.innerHTML = '<p class="text-muted">No tools available</p>';
        return;
    }

    toolsCheckboxes.innerHTML = allTools.map(tool => `
        <label class="checkbox-item" data-tooltip="${escapeHtml(tool.description)}">
            <input type="checkbox" name="tools" value="${tool.name}">
            <span class="checkbox-item-name">${tool.name}</span>
        </label>
    `).join('');
}

function renderAgentsCheckboxes() {
    if (allAgents.length === 0) {
        agentsCheckboxes.innerHTML = '<p class="text-muted">No agents available</p>';
        return;
    }

    agentsCheckboxes.innerHTML = allAgents.map(agent => `
        <label class="checkbox-item" data-tooltip="${escapeHtml(agent.description)}">
            <input type="checkbox" name="agents" value="${agent.name}">
            <span class="checkbox-item-name">${agent.name}</span>
        </label>
    `).join('');
}

// Agent Selection
async function selectAgent(agentName) {
    const detail = await loadAgentDetail(agentName);
    if (!detail) return;

    currentAgent = detail;
    isNewAgent = false;

    // Update UI
    editorTitle.textContent = `Edit: ${agentName}`;
    editorActions.style.display = 'flex';
    editorPlaceholder.style.display = 'none';
    agentForm.style.display = 'block';

    // Populate form
    agentNameInput.value = detail.name;
    agentNameInput.disabled = true; // Can't rename existing agent
    agentDescriptionInput.value = detail.description;
    agentSystemPromptInput.value = detail.system_prompt;

    // Set checkboxes
    setSelectedTools(detail.tools);

    // Update list selection
    renderAgentsList();
}

function setSelectedTools(selectedTools) {
    // Uncheck all
    document.querySelectorAll('input[name="tools"], input[name="agents"]').forEach(cb => {
        cb.checked = false;
    });

    // Check selected ones
    selectedTools.forEach(tool => {
        const checkbox = document.querySelector(`input[value="${tool}"]`);
        if (checkbox) checkbox.checked = true;
    });
}

function getSelectedTools() {
    const selected = [];
    document.querySelectorAll('input[name="tools"]:checked, input[name="agents"]:checked').forEach(cb => {
        selected.push(cb.value);
    });
    return selected;
}

// Form Actions
function showNewAgentForm() {
    currentAgent = null;
    isNewAgent = true;

    editorTitle.textContent = 'New Agent';
    editorActions.style.display = 'none';
    editorPlaceholder.style.display = 'none';
    agentForm.style.display = 'block';

    // Reset form
    agentForm.reset();
    agentNameInput.disabled = false;

    // Clear selection in list
    document.querySelectorAll('.editor-agent-item').forEach(item => {
        item.classList.remove('active');
    });
}

function hideForm() {
    currentAgent = null;
    isNewAgent = false;

    editorTitle.textContent = 'Select an Agent';
    editorActions.style.display = 'none';
    editorPlaceholder.style.display = 'block';
    agentForm.style.display = 'none';
    agentForm.reset();

    // Clear selection in list
    document.querySelectorAll('.editor-agent-item').forEach(item => {
        item.classList.remove('active');
    });
}

async function handleFormSubmit(e) {
    e.preventDefault();

    const agentData = {
        name: agentNameInput.value.trim(),
        description: agentDescriptionInput.value.trim(),
        system_prompt: agentSystemPromptInput.value,
        tools: getSelectedTools()
    };

    try {
        let response;
        if (isNewAgent) {
            response = await fetch('/api/agents', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(agentData)
            });
        } else {
            response = await fetch(`/api/agents/${currentAgent.name}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    description: agentData.description,
                    system_prompt: agentData.system_prompt,
                    tools: agentData.tools
                })
            });
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save agent');
        }

        // Reload agents list
        await loadAgents();

        // Select the saved agent
        await selectAgent(agentData.name);

        // Show success message
        toastSuccess(`Agent "${agentData.name}" saved successfully`);

    } catch (error) {
        toastError(error.message);
    }
}

// Delete Modal
function showDeleteModal() {
    if (!currentAgent) return;
    deleteAgentName.textContent = currentAgent.name;
    deleteModal.classList.add('active');
}

function hideDeleteModal() {
    deleteModal.classList.remove('active');
}

async function handleDelete() {
    if (!currentAgent) return;

    try {
        const response = await fetch(`/api/agents/${currentAgent.name}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete agent');
        }

        const deletedName = currentAgent.name;
        hideDeleteModal();
        hideForm();
        await loadAgents();

        // Show success message
        toastSuccess(`Agent "${deletedName}" deleted`);

    } catch (error) {
        toastError(error.message);
    }
}
