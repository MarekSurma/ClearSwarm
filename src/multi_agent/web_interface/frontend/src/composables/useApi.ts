import type { AgentInfo, AgentDetail, CreateAgentRequest, UpdateAgentRequest, RunAgentRequest, RunAgentResponse, StopAllResponse, ToolInfo } from '@/types/agent'
import type { AgentExecution, ExecutionTree, ExecutionLog, ToolExecution } from '@/types/execution'
import type { GraphData } from '@/types/graph'
import type { ProjectInfo, CreateProjectRequest, CloneProjectRequest } from '@/types/project'
import { useProject } from './useProject'

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
  const { currentProject } = useProject()

  // Helper to add project parameter to URL
  function withProject(url: string): string {
    const separator = url.includes('?') ? '&' : '?'
    return `${url}${separator}project=${encodeURIComponent(currentProject.value.project_dir)}`
  }

  // Agents
  const getAgents = () => request<AgentInfo[]>(withProject('/api/agents'))
  const getAgent = (name: string) => request<AgentInfo>(withProject(`/api/agents/${name}`))
  const getAgentDetail = (name: string) => request<AgentDetail>(withProject(`/api/agents/${name}/detail`))

  const createAgent = (data: CreateAgentRequest) =>
    request<AgentDetail>(withProject('/api/agents'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })

  const updateAgent = (name: string, data: UpdateAgentRequest) =>
    request<AgentDetail>(withProject(`/api/agents/${name}`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })

  const deleteAgent = (name: string) =>
    request<{ message: string }>(withProject(`/api/agents/${name}`), { method: 'DELETE' })

  const runAgent = (data: RunAgentRequest) =>
    request<RunAgentResponse>(withProject('/api/agents/run'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })

  const stopAllAgents = () =>
    request<StopAllResponse>(withProject('/api/agents/stop-all'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })

  const stopAgentTree = (rootId: string) =>
    request<StopAllResponse>(withProject(`/api/agents/stop/${rootId}`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })

  // Tools
  const getTools = () => request<ToolInfo[]>(withProject('/api/tools'))

  // Executions
  const getExecutions = () => request<AgentExecution[]>(withProject('/api/executions'))
  const getExecution = (id: string) => request<AgentExecution>(`/api/executions/${id}`)
  const getExecutionTree = (id: string) => request<ExecutionTree>(`/api/executions/${id}/tree`)
  const getExecutionLog = (id: string) => request<ExecutionLog>(`/api/executions/${id}/log`)
  const getExecutionTools = (id: string) => request<ToolExecution[]>(`/api/executions/${id}/tools`)
  const getExecutionGraph = (id: string) => request<GraphData>(`/api/executions/${id}/graph`)

  // Projects
  const getProjects = () => request<ProjectInfo[]>('/api/projects')
  const createProject = (data: CreateProjectRequest) =>
    request<ProjectInfo>('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
  const cloneProject = (data: CloneProjectRequest) =>
    request<ProjectInfo>('/api/projects/clone', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
  const deleteProject = (projectName: string) =>
    request<{ message: string }>(`/api/projects/${encodeURIComponent(projectName)}`, { method: 'DELETE' })

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
    getProjects,
    createProject,
    cloneProject,
    deleteProject,
  }
}
