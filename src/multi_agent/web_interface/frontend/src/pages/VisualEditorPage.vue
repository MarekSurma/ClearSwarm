<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import type { AgentDetail, AgentInfo, ToolInfo } from '@/types/agent'
import { useAgents } from '@/composables/useAgents'
import { useApi } from '@/composables/useApi'
import { useProject } from '@/composables/useProject'
import { useToast } from 'primevue/usetoast'
import AgentEditorSidebar from '@/components/editor/AgentEditorSidebar.vue'
import VisualGraphCanvas from '@/components/visual-editor/VisualGraphCanvas.vue'
import NodeActionPanel from '@/components/visual-editor/NodeActionPanel.vue'
import AgentEditModal from '@/components/visual-editor/AgentEditModal.vue'
import AgentCreateModal from '@/components/visual-editor/AgentCreateModal.vue'

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
          />
        </div>
      </aside>

      <!-- Right: Graph canvas -->
      <main class="right-panel">
        <div class="graph-wrapper">
          <VisualGraphCanvas
            ref="graphCanvas"
            @node-click="handleNodeClick"
            @deselect="handleDeselect"
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
  grid-template-columns: 280px 1fr;
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
  overflow-y: auto;
}

.right-panel {
  height: 100%;
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
