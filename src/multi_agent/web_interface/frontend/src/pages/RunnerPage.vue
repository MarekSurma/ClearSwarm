<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import ConnectionStatus from '@/components/runner/ConnectionStatus.vue'
import AgentLauncher from '@/components/runner/AgentLauncher.vue'
import AgentCard from '@/components/runner/AgentCard.vue'
import ExecutionMonitor from '@/components/runner/ExecutionMonitor.vue'
import GraphModal from '@/components/graph/GraphModal.vue'
import { useAgents } from '@/composables/useAgents'
import { useExecutions } from '@/composables/useExecutions'
import { useWebSocket } from '@/composables/useWebSocket'
import { useProject } from '@/composables/useProject'

const { agents, loadAgents } = useAgents()
const { executions, rootExecutions, runningExecutions, runningCount, loadExecutions, handleWsMessage, startAutoRefresh, stopAutoRefresh } = useExecutions()
const { isConnected, connect, onMessage, disconnect } = useWebSocket()
const { currentProject } = useProject()

const graphVisible = ref(false)
const graphAgentId = ref<string | null>(null)

onMounted(async () => {
  await Promise.all([loadAgents(), loadExecutions()])
  connect()
  onMessage(handleWsMessage)
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
  disconnect()
})

// Watch for project changes and reload data
watch(
  () => currentProject.value.project_dir,
  async () => {
    await Promise.all([loadAgents(), loadExecutions()])
  }
)

function openGraph(agentId: string) {
  graphAgentId.value = agentId
  graphVisible.value = true
}

function onLaunched() {
  setTimeout(() => loadExecutions(), 1000)
}
</script>

<template>
  <div class="runner-page">
    <header class="page-header">
      <div>
        <h1>Agent Runner</h1>
        <p class="subtitle">Monitor and manage your intelligent agents</p>
      </div>
      <ConnectionStatus :connected="isConnected" :runningCount="runningCount" />
    </header>

    <div class="runner-layout">
      <!-- Left Panel -->
      <aside class="left-panel">
        <div class="panel">
          <AgentLauncher :agents="agents" @launched="onLaunched" />
        </div>
        <div class="panel">
          <h3 class="panel-title">Available Agents</h3>
          <div class="agents-grid">
            <AgentCard v-for="agent in agents" :key="agent.name" :agent="agent" />
            <p v-if="agents.length === 0" class="empty-text">No agents available</p>
          </div>
        </div>
      </aside>

      <!-- Right Panel -->
      <main class="right-panel">
        <div class="panel">
          <ExecutionMonitor
            :executions="executions"
            :rootExecutions="rootExecutions"
            :runningExecutions="runningExecutions"
            @view-graph="openGraph"
            @stopped="loadExecutions"
          />
        </div>
      </main>
    </div>

    <GraphModal
      v-model:visible="graphVisible"
      :agentId="graphAgentId"
    />
  </div>
</template>

<style scoped>
.runner-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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

.runner-layout {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 1.5rem;
  align-items: start;
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.panel {
  border: 1px solid var(--p-surface-200);
  border-radius: 10px;
  padding: 1.25rem;
}

.panel-title {
  margin: 0 0 0.75rem 0;
  font-size: 1rem;
  font-weight: 600;
}

.agents-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 300px;
  overflow-y: auto;
}

.empty-text {
  color: var(--p-text-muted-color);
  text-align: center;
  padding: 1rem;
}

@media (max-width: 900px) {
  .runner-layout {
    grid-template-columns: 1fr;
  }
}
</style>
