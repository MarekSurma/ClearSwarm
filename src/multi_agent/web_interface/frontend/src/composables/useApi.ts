import type { AgentInfo, AgentDetail, CreateAgentRequest, UpdateAgentRequest, RunAgentRequest, RunAgentResponse, StopAllResponse, ToolInfo } from '@/types/agent'
import type { AgentExecution, ExecutionTree, ExecutionLog, ToolExecution } from '@/types/execution'
import type { GraphData } from '@/types/graph'

const API_BASE = ''

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, options)
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

export function useApi() {
  // Agents
  const getAgents = () => request<AgentInfo[]>('/api/agents')
  const getAgent = (name: string) => request<AgentInfo>(`/api/agents/${name}`)
  const getAgentDetail = (name: string) => request<AgentDetail>(`/api/agents/${name}/detail`)

  const createAgent = (data: CreateAgentRequest) =>
    request<AgentDetail>('/api/agents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })

  const updateAgent = (name: string, data: UpdateAgentRequest) =>
    request<AgentDetail>(`/api/agents/${name}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })

  const deleteAgent = (name: string) =>
    request<{ message: string }>(`/api/agents/${name}`, { method: 'DELETE' })

  const runAgent = (data: RunAgentRequest) =>
    request<RunAgentResponse>('/api/agents/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })

  const stopAllAgents = () =>
    request<StopAllResponse>('/api/agents/stop-all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })

  const stopAgentTree = (rootId: string) =>
    request<StopAllResponse>(`/api/agents/stop/${rootId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })

  // Tools
  const getTools = () => request<ToolInfo[]>('/api/tools')

  // Executions
  const getExecutions = () => request<AgentExecution[]>('/api/executions')
  const getExecution = (id: string) => request<AgentExecution>(`/api/executions/${id}`)
  const getExecutionTree = (id: string) => request<ExecutionTree>(`/api/executions/${id}/tree`)
  const getExecutionLog = (id: string) => request<ExecutionLog>(`/api/executions/${id}/log`)
  const getExecutionTools = (id: string) => request<ToolExecution[]>(`/api/executions/${id}/tools`)
  const getExecutionGraph = (id: string) => request<GraphData>(`/api/executions/${id}/graph`)

  return {
    getAgents,
    getAgent,
    getAgentDetail,
    createAgent,
    updateAgent,
    deleteAgent,
    runAgent,
    stopAllAgents,
    stopAgentTree,
    getTools,
    getExecutions,
    getExecution,
    getExecutionTree,
    getExecutionLog,
    getExecutionTools,
    getExecutionGraph,
  }
}
