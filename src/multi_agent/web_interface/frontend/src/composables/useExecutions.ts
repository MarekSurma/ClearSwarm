import { shallowRef, triggerRef, computed, onUnmounted } from 'vue'
import type { AgentExecution } from '@/types/execution'
import type { WebSocketMessage } from '@/types/websocket'
import { useApi } from './useApi'

const executions = shallowRef<AgentExecution[]>([])

function mergeExecutions(incoming: AgentExecution[]) {
  const current = executions.value
  if (current.length === 0) {
    executions.value = incoming
    return
  }

  const currentMap = new Map(current.map((e) => [e.agent_id, e]))
  let changed = incoming.length !== current.length

  const merged = incoming.map((inc) => {
    const existing = currentMap.get(inc.agent_id)
    if (
      existing &&
      existing.current_state === inc.current_state &&
      existing.is_running === inc.is_running &&
      existing.completed_at === inc.completed_at &&
      existing.question === inc.question &&
      existing.final_response === inc.final_response
    ) {
      return existing // reuse existing reference — no reactivity trigger
    }
    changed = true
    return inc
  })

  if (changed) {
    executions.value = merged
  }
}

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
      const data = await api.getExecutions()
      mergeExecutions(data)
    } catch (error) {
      console.error('Failed to load executions:', error)
    }
  }

  function handleWsMessage(message: WebSocketMessage) {
    switch (message.type) {
      case 'executions_update':
        mergeExecutions(message.executions as unknown as AgentExecution[])
        break
      case 'running_agents': {
        let changed = false
        for (const exec of executions.value) {
          const runningAgent = message.agents.find(
            (a) => a.agent_id === exec.agent_id
          )
          if (runningAgent && exec.current_state !== runningAgent.current_state) {
            exec.current_state = runningAgent.current_state
            exec.is_running = true
            changed = true
          }
        }
        if (changed) triggerRef(executions)
        break
      }
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
