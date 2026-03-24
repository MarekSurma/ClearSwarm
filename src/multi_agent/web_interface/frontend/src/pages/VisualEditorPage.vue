<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import Card from 'primevue/card'
import type { AgentDetail, ToolInfo } from '@/types/agent'
import { useAgents } from '@/composables/useAgents'
import { useApi } from '@/composables/useApi'
import { useProject } from '@/composables/useProject'
import { useToast } from 'primevue/usetoast'
import { toDisplayName } from '@/utils/nameFormatting'
import AgentEditorSidebar from '@/components/editor/AgentEditorSidebar.vue'
import VisualGraphCanvas from '@/components/visual-editor/VisualGraphCanvas.vue'
import AgentEditModal from '@/components/visual-editor/AgentEditModal.vue'
import AgentCreateModal from '@/components/visual-editor/AgentCreateModal.vue'
import ToolsSidebar from '@/components/visual-editor/ToolsSidebar.vue'

const { agents, loadAgents } = useAgents()
const api = useApi()
const { currentProject } = useProject()
const toast = useToast()

const tools = ref<ToolInfo[]>([])
const selectedAgentName = ref<string | null>(null)
const hoveredGraphAgentName = ref<string | null>(null)
const selectedNodeAgentDetail = ref<AgentDetail | null>(null)
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
  selectedNodeAgentDetail.value = null

  // Build graph
  const allAgentNames = agents.value.map((a) => a.name)
  if (graphCanvas.value) {
    graphCanvas.value.buildGraph(name, allAgentNames)
  }
}

async function handleNodeClick(nodeId: string) {
  // Only handle agent nodes - open the edit modal directly
  if (nodeId.startsWith('agent::')) {
    const agentName = nodeId.replace('agent::', '')
    try {
      selectedNodeAgentDetail.value = await api.getAgentDetail(agentName)
      showEditModal.value = true
    } catch (error) {
      console.error('Failed to load agent detail:', error)
      selectedNodeAgentDetail.value = null
    }
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

}

async function handleRemoveSelfLoop(agentName: string) {
  try {
    const agentDetail = await api.getAgentDetail(agentName)
    const updatedTools = agentDetail.tools.filter((t) => t !== agentName)

    await api.updateAgent(agentName, {
      description: agentDetail.description,
      system_prompt: agentDetail.system_prompt,
      tools: updatedTools,
    })

    toast.add({
      severity: 'success',
      summary: 'Self-Reference Removed',
      detail: `Agent "${toDisplayName(agentName)}" can no longer call itself`,
      life: 3000,
    })

  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'Failed to remove self-reference',
      life: 5000,
    })
  }
}

async function handleModalSaved() {
  // Description/prompt edits don't change graph structure
  await loadAgents()
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
      <p class="subtitle">Select an agent to view its graph. Click a node to edit it. Drag agents or tools from the side panels onto nodes to assign them.</p>
    </header>

    <div class="editor-layout">
      <!-- Full-width graph canvas -->
      <div class="graph-wrapper">
        <VisualGraphCanvas
          ref="graphCanvas"
          @node-click="handleNodeClick"
          @drop-agent="handleDropAgent"
          @drop-tool="handleDropTool"
          @remove-node="handleQuickRemoveNode"
          @remove-self-loop="handleRemoveSelfLoop"
          @node-hover="(name) => hoveredGraphAgentName = name"
        />
      </div>

      <!-- Floating left: Agent list -->
      <aside class="left-panel">
        <Card class="floating-card">
          <template #content>
            <AgentEditorSidebar
              :agents="agents"
              :selectedName="selectedAgentName"
              :hoveredName="hoveredGraphAgentName"
              @select="selectAgent"
              @new="handleNewAgent"
              @delete="handleDeleteAgent"
              @clone="handleCloneAgent"
            />
          </template>
        </Card>
      </aside>

      <!-- Floating right: Tools list -->
      <aside class="right-panel">
        <Card class="floating-card">
          <template #content>
            <ToolsSidebar :tools="tools" />
          </template>
        </Card>
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
  position: relative;
  height: calc(100vh - 180px);
}

.graph-wrapper {
  position: absolute;
  inset: 0;
  border: 1px solid var(--p-surface-200);
  border-radius: 10px;
  overflow: hidden;
}

.left-panel {
  position: absolute;
  top: 70px;
  left: 0.75rem;
  width: 250px;
  max-height: calc(100% - 70px - 0.75rem);
  z-index: 2;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.right-panel {
  position: absolute;
  top: 70px;
  right: 0.75rem;
  width: 220px;
  max-height: calc(100% - 70px - 0.75rem);
  z-index: 2;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.floating-card {
  max-height: 100%;
  overflow: hidden;
  background: #aee9ff;
}

.floating-card :deep(.p-card-body) {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100%;
  padding: 1rem;
}

.floating-card :deep(.p-card-content) {
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

@media (max-width: 768px) {
  .left-panel,
  .right-panel {
    position: static;
    width: 100%;
    max-height: none;
  }

  .editor-layout {
    display: flex;
    flex-direction: column;
  }

  .graph-wrapper {
    position: relative;
    height: 400px;
  }
}
</style>
