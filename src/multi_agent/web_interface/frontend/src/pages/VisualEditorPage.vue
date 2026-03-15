<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import type { AgentDetail, AgentInfo, ToolInfo } from '@/types/agent'
import { useAgents } from '@/composables/useAgents'
import { useApi } from '@/composables/useApi'
import { useProject } from '@/composables/useProject'
import { useToast } from 'primevue/usetoast'
import { toDisplayName } from '@/utils/nameFormatting'
import AgentEditorSidebar from '@/components/editor/AgentEditorSidebar.vue'
import VisualGraphCanvas from '@/components/visual-editor/VisualGraphCanvas.vue'
import NodeActionPanel from '@/components/visual-editor/NodeActionPanel.vue'
import AgentEditModal from '@/components/visual-editor/AgentEditModal.vue'
import AgentCreateModal from '@/components/visual-editor/AgentCreateModal.vue'
import ToolsSidebar from '@/components/visual-editor/ToolsSidebar.vue'

const { agents, loadAgents } = useAgents()
const api = useApi()
const { currentProject } = useProject()
const toast = useToast()

const tools = ref<ToolInfo[]>([])
const selectedAgentName = ref<string | null>(null)
const selectedNodeId = ref<string | null>(null)
const selectedNodeAgentDetail = ref<AgentDetail | null>(null)
const parentAgents = ref<string[]>([])
const isRootNode = ref(false)
const showEditModal = ref(false)
const showCreateModal = ref(false)
const graphCanvas = ref<InstanceType<typeof VisualGraphCanvas> | null>(null)

onMounted(async () => {
  await Promise.all([loadAgents(), loadTools()])
})

// Watch for project changes and reload data
watch(
  () => currentProject.value.project_dir,
  async () => {
    // Clear selection and reload
    selectedAgentName.value = null
    selectedNodeId.value = null
    selectedNodeAgentDetail.value = null
    await Promise.all([loadAgents(), loadTools()])
  }
)

async function loadTools() {
  try {
    tools.value = await api.getTools()
  } catch (error) {
    console.error('Failed to load tools:', error)
  }
}

async function selectAgent(name: string) {
  selectedAgentName.value = name
  selectedNodeId.value = null
  selectedNodeAgentDetail.value = null

  // Build graph
  const allAgentNames = agents.value.map((a) => a.name)
  if (graphCanvas.value) {
    graphCanvas.value.buildGraph(name, allAgentNames)
  }
}

async function handleNodeClick(nodeId: string) {
  selectedNodeId.value = nodeId

  // Determine if this is the root node
  if (nodeId.startsWith('agent::')) {
    const agentName = nodeId.replace('agent::', '')
    isRootNode.value = agentName === selectedAgentName.value
  } else {
    isRootNode.value = false
  }

  // Load agent detail for the clicked node
  if (nodeId.startsWith('agent::')) {
    const agentName = nodeId.replace('agent::', '')
    try {
      selectedNodeAgentDetail.value = await api.getAgentDetail(agentName)
    } catch (error) {
      console.error('Failed to load agent detail:', error)
      selectedNodeAgentDetail.value = null
    }
  } else if (nodeId.startsWith('tool::')) {
    // For tool nodes, we don't need agent detail
    selectedNodeAgentDetail.value = null
  }

  // Get parent agents
  parentAgents.value = graphCanvas.value?.getParentAgents(nodeId) ?? []
}

function handleDeselect() {
  selectedNodeId.value = null
  selectedNodeAgentDetail.value = null
  parentAgents.value = []
}

async function handleAddTool(toolName: string) {
  if (!selectedNodeAgentDetail.value) return

  const agentName = selectedNodeAgentDetail.value.name
  const updatedTools = [...selectedNodeAgentDetail.value.tools, toolName]

  try {
    await api.updateAgent(agentName, {
      description: selectedNodeAgentDetail.value.description,
      system_prompt: selectedNodeAgentDetail.value.system_prompt,
      tools: updatedTools,
    })

    toast.add({
      severity: 'success',
      summary: 'Tool Added',
      detail: `Tool "${toolName}" added to agent "${agentName}"`,
      life: 3000,
    })

    // Update local detail cache and add node incrementally
    selectedNodeAgentDetail.value = { ...selectedNodeAgentDetail.value, tools: updatedTools }
    graphCanvas.value?.addToolNode(agentName, toolName)
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'Failed to add tool',
      life: 5000,
    })
  }
}

async function handleAddAgent(subAgentName: string) {
  if (!selectedNodeAgentDetail.value) return

  const agentName = selectedNodeAgentDetail.value.name
  const updatedTools = [...selectedNodeAgentDetail.value.tools, subAgentName]

  try {
    await api.updateAgent(agentName, {
      description: selectedNodeAgentDetail.value.description,
      system_prompt: selectedNodeAgentDetail.value.system_prompt,
      tools: updatedTools,
    })

    toast.add({
      severity: 'success',
      summary: 'Sub-Agent Added',
      detail: `Agent "${subAgentName}" added to "${agentName}"`,
      life: 3000,
    })

    // Update local detail cache and add node incrementally
    selectedNodeAgentDetail.value = { ...selectedNodeAgentDetail.value, tools: updatedTools }
    await loadAgents() // Refresh agent list for allAgents
    const allAgentNames = agents.value.map((a) => a.name)
    await graphCanvas.value?.addSubAgentNode(agentName, subAgentName, allAgentNames)
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'Failed to add sub-agent',
      life: 5000,
    })
  }
}

async function handleDropAgent(droppedAgentName: string, targetAgentName: string) {
  // Load the target agent detail so we can update its tools list
  try {
    const targetDetail = await api.getAgentDetail(targetAgentName)

    // Check if already assigned
    if (targetDetail.tools.includes(droppedAgentName)) {
      toast.add({
        severity: 'warn',
        summary: 'Already Added',
        detail: `"${toDisplayName(droppedAgentName)}" is already in "${toDisplayName(targetAgentName)}"`,
        life: 3000,
      })
      return
    }

    const updatedTools = [...targetDetail.tools, droppedAgentName]

    await api.updateAgent(targetAgentName, {
      description: targetDetail.description,
      system_prompt: targetDetail.system_prompt,
      tools: updatedTools,
    })

    toast.add({
      severity: 'success',
      summary: 'Sub-Agent Added',
      detail: `Agent "${toDisplayName(droppedAgentName)}" added to "${toDisplayName(targetAgentName)}"`,
      life: 3000,
    })

    // Update graph incrementally
    await loadAgents()
    const allAgentNames = agents.value.map((a) => a.name)
    await graphCanvas.value?.addSubAgentNode(targetAgentName, droppedAgentName, allAgentNames)

    // If the target agent was the selected node, refresh its detail
    if (selectedNodeId.value === `agent::${targetAgentName}` && selectedNodeAgentDetail.value) {
      selectedNodeAgentDetail.value = { ...selectedNodeAgentDetail.value, tools: updatedTools }
    }
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'Failed to add sub-agent',
      life: 5000,
    })
  }
}

async function handleDropTool(toolName: string, targetAgentName: string) {
  try {
    const targetDetail = await api.getAgentDetail(targetAgentName)

    if (targetDetail.tools.includes(toolName)) {
      toast.add({
        severity: 'warn',
        summary: 'Already Added',
        detail: `"${toDisplayName(toolName)}" is already in "${toDisplayName(targetAgentName)}"`,
        life: 3000,
      })
      return
    }

    const updatedTools = [...targetDetail.tools, toolName]

    await api.updateAgent(targetAgentName, {
      description: targetDetail.description,
      system_prompt: targetDetail.system_prompt,
      tools: updatedTools,
    })

    toast.add({
      severity: 'success',
      summary: 'Tool Added',
      detail: `Tool "${toDisplayName(toolName)}" added to "${toDisplayName(targetAgentName)}"`,
      life: 3000,
    })

    graphCanvas.value?.addToolNode(targetAgentName, toolName)

    if (selectedNodeId.value === `agent::${targetAgentName}` && selectedNodeAgentDetail.value) {
      selectedNodeAgentDetail.value = { ...selectedNodeAgentDetail.value, tools: updatedTools }
    }
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'Failed to add tool',
      life: 5000,
    })
  }
}

async function handleQuickRemoveNode(nodeId: string) {
  const parents = graphCanvas.value?.getParentAgents(nodeId) ?? []
  if (parents.length === 0) return

  // Determine what to remove
  let itemToRemove = ''
  if (nodeId.startsWith('agent::')) {
    itemToRemove = nodeId.replace('agent::', '')
  } else if (nodeId.startsWith('tool::')) {
    const match = nodeId.match(/^tool::(.+?)::from::/)
    if (match) itemToRemove = match[1]
  }
  if (!itemToRemove) return

  // Remove from all parents
  for (const parentAgentName of parents) {
    try {
      const parentDetail = await api.getAgentDetail(parentAgentName)
      const updatedTools = parentDetail.tools.filter((t) => t !== itemToRemove)

      await api.updateAgent(parentAgentName, {
        description: parentDetail.description,
        system_prompt: parentDetail.system_prompt,
        tools: updatedTools,
      })

      graphCanvas.value?.removeEdgeFromParent(nodeId, parentAgentName)
    } catch (error: any) {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: error.message || 'Failed to remove',
        life: 5000,
      })
      return
    }
  }

  toast.add({
    severity: 'success',
    summary: 'Removed',
    detail: `Removed "${toDisplayName(itemToRemove)}"`,
    life: 3000,
  })

  // Clear selection if this was the selected node
  if (selectedNodeId.value === nodeId) {
    selectedNodeId.value = null
    selectedNodeAgentDetail.value = null
  }
}

function handleEditTexts() {
  showEditModal.value = true
}

async function handleRemoveFromParent(parentAgentName: string) {
  if (!selectedNodeId.value) return

  let itemToRemove = ''

  // Determine what to remove
  if (selectedNodeId.value.startsWith('agent::')) {
    itemToRemove = selectedNodeId.value.replace('agent::', '')
  } else if (selectedNodeId.value.startsWith('tool::')) {
    const match = selectedNodeId.value.match(/^tool::(.+?)::from::/)
    if (match) itemToRemove = match[1]
  }

  if (!itemToRemove) return

  try {
    // Load parent agent detail
    const parentDetail = await api.getAgentDetail(parentAgentName)

    // Remove item from parent's tools
    const updatedTools = parentDetail.tools.filter((t) => t !== itemToRemove)

    await api.updateAgent(parentAgentName, {
      description: parentDetail.description,
      system_prompt: parentDetail.system_prompt,
      tools: updatedTools,
    })

    toast.add({
      severity: 'success',
      summary: 'Removed',
      detail: `Removed "${itemToRemove}" from "${parentAgentName}"`,
      life: 3000,
    })

    // Remove from graph incrementally
    const removedNodeId = selectedNodeId.value
    graphCanvas.value?.removeEdgeFromParent(removedNodeId, parentAgentName)
    selectedNodeId.value = null
    selectedNodeAgentDetail.value = null
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'Failed to remove',
      life: 5000,
    })
  }
}

async function handleModalSaved() {
  // Description/prompt edits don't change graph structure
  await loadAgents()
  selectedNodeId.value = null
  selectedNodeAgentDetail.value = null
}

function handleNewAgent() {
  showCreateModal.value = true
}

async function handleAgentCreated(agentName: string) {
  // Reload agents and select the newly created one
  await loadAgents()
  selectAgent(agentName)
}

async function handleCloneAgent(source: string, newName: string) {
  try {
    const cloned = await api.cloneAgent(source, newName)

    toast.add({
      severity: 'success',
      summary: 'Agent Cloned',
      detail: `Created "${toDisplayName(cloned.name)}" from "${toDisplayName(source)}"`,
      life: 3000,
    })

    await loadAgents()
    selectAgent(cloned.name)
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'Failed to clone agent',
      life: 5000,
    })
  }
}

async function handleDeleteAgent(agentName: string) {
  try {
    await api.deleteAgent(agentName)

    toast.add({
      severity: 'success',
      summary: 'Agent Deleted',
      detail: `Agent "${agentName}" has been deleted`,
      life: 3000,
    })

    // Clear selection if the deleted agent was selected
    if (selectedAgentName.value === agentName) {
      selectedAgentName.value = null
      selectedNodeId.value = null
      selectedNodeAgentDetail.value = null
    }

    await loadAgents()
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'Failed to delete agent',
      life: 5000,
    })
  }
}
</script>

<template>
  <div class="editor-page">
    <header class="page-header">
      <h1>Visual Editor</h1>
      <p class="subtitle">Visually design your agent network</p>
    </header>

    <div class="editor-layout">
      <!-- Left: Agent list -->
      <aside class="left-panel">
        <div class="panel">
          <AgentEditorSidebar
            :agents="agents"
            :selectedName="selectedAgentName"
            @select="selectAgent"
            @new="handleNewAgent"
            @delete="handleDeleteAgent"
            @clone="handleCloneAgent"
          />
        </div>
      </aside>

      <!-- Center: Graph canvas -->
      <main class="center-panel">
        <div class="graph-wrapper">
          <VisualGraphCanvas
            ref="graphCanvas"
            @node-click="handleNodeClick"
            @deselect="handleDeselect"
            @drop-agent="handleDropAgent"
            @drop-tool="handleDropTool"
            @remove-node="handleQuickRemoveNode"
          />

          <!-- Node Action Panel -->
          <NodeActionPanel
            :nodeId="selectedNodeId"
            :agentDetail="selectedNodeAgentDetail"
            :allAgents="agents"
            :allTools="tools"
            :parentAgents="parentAgents"
            :isRootNode="isRootNode"
            @add-tool="handleAddTool"
            @add-agent="handleAddAgent"
            @edit-texts="handleEditTexts"
            @remove-from-parent="handleRemoveFromParent"
          />
        </div>
      </main>

      <!-- Right: Tools list -->
      <aside class="right-panel">
        <div class="panel">
          <ToolsSidebar :tools="tools" />
        </div>
      </aside>
    </div>

    <!-- Agent Edit Modal -->
    <AgentEditModal
      v-model:visible="showEditModal"
      :agentDetail="selectedNodeAgentDetail"
      @saved="handleModalSaved"
    />

    <!-- Agent Create Modal -->
    <AgentCreateModal
      v-model:visible="showCreateModal"
      @saved="handleAgentCreated"
    />
  </div>
</template>

<style scoped>
.editor-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.page-header h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
}

.subtitle {
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
  margin-top: 0.25rem;
}

.editor-layout {
  display: grid;
  grid-template-columns: 280px 1fr 260px;
  gap: 1.5rem;
  height: calc(100vh - 180px);
}

.left-panel {
  height: 100%;
  overflow: hidden;
}

.panel {
  border: 1px solid var(--p-surface-200);
  border-radius: 10px;
  padding: 1.25rem;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.center-panel {
  height: 100%;
  min-width: 0;
}

.right-panel {
  height: 100%;
  overflow: hidden;
}

.graph-wrapper {
  position: relative;
  height: 100%;
  border: 1px solid var(--p-surface-200);
  border-radius: 10px;
  overflow: hidden;
}

@media (max-width: 768px) {
  .editor-layout {
    grid-template-columns: 1fr;
  }
}
</style>
