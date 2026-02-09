import { ref, computed, onUnmounted } from 'vue'
import type { AgentExecution } from '@/types/execution'
import type { WebSocketMessage } from '@/types/websocket'
import { useApi } from './useApi'

const executions = ref<AgentExecution[]>([])

export function useExecutions() {
  const api = useApi()
  let autoRefreshInterval: ReturnType<typeof setInterval> | null = null

  const rootExecutions = computed(() =>
    executions.value.filter((e) => e.parent_agent_id === null)
  )

  const runningExecutions = computed(() =>
    executions.value.filter((e) => e.is_running)
  )

  const runningCount = computed(() => runningExecutions.value.length)

  async function loadExecutions() {
    try {
      executions.value = await api.getExecutions()
    } catch (error) {
      console.error('Failed to load executions:', error)
    }
  }

  function handleWsMessage(message: WebSocketMessage) {
    switch (message.type) {
      case 'executions_update':
        executions.value = message.executions as unknown as AgentExecution[]
        break
      case 'running_agents':
        // Update running state of executions
        executions.value = executions.value.map((exec) => {
          const runningAgent = message.agents.find(
            (a) => a.agent_id === exec.agent_id
          )
          if (runningAgent) {
            return {
              ...exec,
              current_state: runningAgent.current_state,
              is_running: true,
            }
          }
          return exec
        })
        break
      case 'agent_completed':
        loadExecutions()
        break
      case 'agent_update':
        loadExecutions()
        break
    }
  }

  function startAutoRefresh() {
    stopAutoRefresh()
    autoRefreshInterval = setInterval(() => loadExecutions(), 3000)
  }

  function stopAutoRefresh() {
    if (autoRefreshInterval) {
      clearInterval(autoRefreshInterval)
      autoRefreshInterval = null
    }
  }

  onUnmounted(() => {
    stopAutoRefresh()
  })

  return {
    executions,
    rootExecutions,
    runningExecutions,
    runningCount,
    loadExecutions,
    handleWsMessage,
    startAutoRefresh,
    stopAutoRefresh,
  }
}
