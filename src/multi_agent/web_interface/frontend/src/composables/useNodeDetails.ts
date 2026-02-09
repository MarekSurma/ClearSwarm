import { ref } from 'vue'
import type { ExecutionLog, LogMessage, ToolExecution } from '@/types/execution'
import { useApi } from './useApi'

export function useNodeDetails() {
  const api = useApi()

  const selectedNodeId = ref<string | null>(null)
  const isRunning = ref(false)
  const agentLog = ref<ExecutionLog | null>(null)
  const toolDetail = ref<ToolExecution | null>(null)
  const nodeType = ref<'agent' | 'tool' | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  let refreshInterval: ReturnType<typeof setInterval> | null = null
  let lastMessageCount = 0

  async function loadAgentDetails(agentId: string) {
    nodeType.value = 'agent'
    toolDetail.value = null
    error.value = null

    if (selectedNodeId.value !== agentId) {
      agentLog.value = null
      lastMessageCount = 0
      loading.value = true
    }

    selectedNodeId.value = agentId

    try {
      const logData = await api.getExecutionLog(agentId)
      agentLog.value = logData
      lastMessageCount = logData.interactions?.length || 0

      isRunning.value = logData.session_ended_explicitly === null
      if (isRunning.value) {
        startRefresh()
      } else {
        stopRefresh()
      }
    } catch (e: any) {
      if (e.message?.includes('404')) {
        // Log not yet available
        error.value = null
      } else {
        error.value = e.message || 'Failed to load details'
      }
    } finally {
      loading.value = false
    }
  }

  async function loadToolDetails(toolId: string, parentAgentId: string) {
    nodeType.value = 'tool'
    agentLog.value = null
    error.value = null

    if (selectedNodeId.value !== toolId) {
      toolDetail.value = null
      loading.value = true
    }

    selectedNodeId.value = toolId

    try {
      const tools = await api.getExecutionTools(parentAgentId)
      const tool = tools.find((t) => t.tool_execution_id === toolId)
      if (!tool) throw new Error('Tool not found')
      toolDetail.value = tool

      isRunning.value = tool.is_running
      if (isRunning.value) {
        startRefresh()
      } else {
        stopRefresh()
      }
    } catch (e: any) {
      error.value = e.message || 'Failed to load tool details'
    } finally {
      loading.value = false
    }
  }

  function startRefresh() {
    stopRefresh()
    refreshInterval = setInterval(async () => {
      if (!selectedNodeId.value) {
        stopRefresh()
        return
      }
      try {
        if (nodeType.value === 'agent') {
          const logData = await api.getExecutionLog(selectedNodeId.value)
          agentLog.value = logData
          lastMessageCount = logData.interactions?.length || 0
          if (logData.session_ended_explicitly !== null) {
            isRunning.value = false
            stopRefresh()
          }
        }
      } catch {
        // Ignore refresh errors
      }
    }, 1000)
  }

  function stopRefresh() {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }

  function clearSelection() {
    stopRefresh()
    selectedNodeId.value = null
    agentLog.value = null
    toolDetail.value = null
    nodeType.value = null
    isRunning.value = false
    loading.value = false
    error.value = null
    lastMessageCount = 0
  }

  return {
    selectedNodeId,
    isRunning,
    agentLog,
    toolDetail,
    nodeType,
    loading,
    error,
    loadAgentDetails,
    loadToolDetails,
    clearSelection,
    stopRefresh,
  }
}
