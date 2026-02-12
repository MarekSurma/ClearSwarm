<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import type { AgentDetail, ToolInfo } from '@/types/agent'
import { useAgents } from '@/composables/useAgents'
import { useApi } from '@/composables/useApi'
import { useProject } from '@/composables/useProject'
import AgentEditorSidebar from '@/components/editor/AgentEditorSidebar.vue'
import AgentEditorForm from '@/components/editor/AgentEditorForm.vue'

const { agents, loadAgents } = useAgents()
const api = useApi()
const { currentProject } = useProject()

const currentAgent = ref<AgentDetail | null>(null)
const isNew = ref(false)
const showForm = ref(false)
const tools = ref<ToolInfo[]>([])

onMounted(async () => {
  await Promise.all([loadAgents(), loadTools()])
})

// Watch for project changes and reload data
watch(
  () => currentProject.value.project_dir,
  async () => {
    // Close form and reload everything
    currentAgent.value = null
    isNew.value = false
    showForm.value = false
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
  try {
    const detail = await api.getAgentDetail(name)
    currentAgent.value = detail
    isNew.value = false
    showForm.value = true
  } catch (error) {
    console.error('Failed to load agent detail:', error)
  }
}

function startNewAgent() {
  currentAgent.value = null
  isNew.value = true
  showForm.value = true
}

async function onSaved(name: string) {
  await loadAgents()
  await selectAgent(name)
}

async function onDeleted() {
  currentAgent.value = null
  isNew.value = false
  showForm.value = false
  await loadAgents()
}

function onCancel() {
  currentAgent.value = null
  isNew.value = false
  showForm.value = false
}
</script>

<template>
  <div class="editor-page">
    <header class="page-header">
      <h1>Agent Editor</h1>
      <p class="subtitle">Create and configure your agents</p>
    </header>

    <div class="editor-layout">
      <!-- Left: Agent list -->
      <aside class="left-panel">
        <div class="panel">
          <AgentEditorSidebar
            :agents="agents"
            :selectedName="currentAgent?.name ?? null"
            @select="selectAgent"
            @new="startNewAgent"
          />
        </div>
      </aside>

      <!-- Right: Editor form -->
      <main class="right-panel">
        <div class="panel">
          <template v-if="showForm">
            <AgentEditorForm
              :agent="currentAgent"
              :isNew="isNew"
              :tools="tools"
              :allAgents="agents"
              @saved="onSaved"
              @deleted="onDeleted"
              @cancel="onCancel"
            />
          </template>
          <div v-else class="placeholder">
            <i class="pi pi-pencil placeholder-icon" />
            <p>Select an agent from the list to edit, or click <strong>+</strong> to create one.</p>
          </div>
        </div>
      </main>
    </div>
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
  align-items: start;
}

.panel {
  border: 1px solid var(--p-surface-200);
  border-radius: 10px;
  padding: 1.25rem;
}

.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  text-align: center;
  color: var(--p-text-muted-color);
}

.placeholder-icon {
  font-size: 2rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

@media (max-width: 768px) {
  .editor-layout {
    grid-template-columns: 1fr;
  }
}
</style>
