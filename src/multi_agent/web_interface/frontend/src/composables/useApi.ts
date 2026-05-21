import type { AgentInfo, AgentDetail, CreateAgentRequest, UpdateAgentRequest, RunAgentRequest, RunAgentResponse, StopAllResponse, ToolInfo } from '@/types/agent'
import type { AgentExecution, ExecutionTree, ExecutionLog, ToolExecution } from '@/types/execution'
import type { GraphData, GraphResponse } from '@/types/graph'
import type { ProjectInfo, CreateProjectRequest, CloneProjectRequest } from '@/types/project'
import type { ScheduleInfo, CreateScheduleRequest, UpdateScheduleRequest } from '@/types/schedule'
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

  // Returns a URL (not a JSON request) — used directly as <img src> / vis-network image.
  const getToolIconUrl = (toolName: string) =>
    withProject(`/api/tools/${encodeURIComponent(toolName)}/icon`)

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

  const cloneAgent = (name: string, newName: string) =>
    request<AgentDetail>(withProject(`/api/agents/${name}/clone`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_name: newName }),
    })

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
  const deleteExecution = (id: string) => request<{ message: string }>(`/api/executions/${id}`, { method: 'DELETE' })
  // ETag-aware graph fetching (legacy, kept for backward compatibility)
  let _graphEtag: string | null = null

  const resetGraphEtag = () => { _graphEtag = null }

  const getExecutionGraph = async (id: string): Promise<GraphData | null> => {
    const headers: Record<string, string> = {}
    if (_graphEtag) headers['If-None-Match'] = _graphEtag

    const response = await fetch(`${API_BASE}/api/executions/${id}/graph`, { headers })
    if (response.status === 304) return null  // no change
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }
    _graphEtag = response.headers.get('etag')
    return response.json()
  }

  // Sequence-based incremental graph updates
  let _graphSequence: number = 0

  const resetGraphSequence = () => { _graphSequence = 0 }

  const getGraphDelta = async (id: string): Promise<GraphResponse | null> => {
    const response = await fetch(
      `${API_BASE}/api/executions/${id}/graph/delta?since=${_graphSequence}`
    )
    if (response.status === 304) return null
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }
    const data = await response.json()
    _graphSequence = data.current_sequence
    return data
  }

  // Graph layout persistence
  type GraphLayoutPositions = Record<string, { x: number; y: number }>

  const getGraphLayout = async (agentId: string, layout: string): Promise<GraphLayoutPositions> => {
    const url = withProject(`/api/executions/${agentId}/graph/layout`) + `&layout=${encodeURIComponent(layout)}`
    try {
      const response = await fetch(`${API_BASE}${url}`)
      if (!response.ok) return {}
      const data = await response.json().catch(() => null) as { positions?: GraphLayoutPositions } | null
      return data?.positions ?? {}
    } catch {
      return {}
    }
  }

  const putGraphLayout = async (agentId: string, layout: string, positions: GraphLayoutPositions): Promise<void> => {
    const url = withProject(`/api/executions/${agentId}/graph/layout`) + `&layout=${encodeURIComponent(layout)}`
    try {
      await fetch(`${API_BASE}${url}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ positions }),
      })
    } catch {
      // best-effort persistence; ignore network errors
    }
  }

  const deleteGraphLayout = async (agentId: string, layout?: string): Promise<void> => {
    let url = withProject(`/api/executions/${agentId}/graph/layout`)
    if (layout) url += `&layout=${encodeURIComponent(layout)}`
    try {
      await fetch(`${API_BASE}${url}`, { method: 'DELETE' })
    } catch {
      // ignore
    }
  }

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

  // Project files
  type FileEntry = { name: string; path: string; is_dir: boolean; size: number }
  type ListResponse = { project_dir: string; path: string; entries: FileEntry[] }

  const listProjectFiles = (path: string = '') => {
    const projectDir = encodeURIComponent(currentProject.value.project_dir)
    const q = path ? `?path=${encodeURIComponent(path)}` : ''
    return request<ListResponse>(`/api/projects/${projectDir}/files${q}`)
  }

  const uploadProjectFile = async (file: File, path: string = '') => {
    const projectDir = encodeURIComponent(currentProject.value.project_dir)
    const form = new FormData()
    form.append('file', file)
    form.append('path', path)
    const response = await fetch(`${API_BASE}/api/projects/${projectDir}/files/upload`, {
      method: 'POST',
      body: form,
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }
    return response.json() as Promise<{ path: string; size: number }>
  }

  const getProjectFileContent = (path: string) => {
    const projectDir = encodeURIComponent(currentProject.value.project_dir)
    return request<{ path: string; name: string; size: number; truncated: boolean; content: string }>(
      `/api/projects/${projectDir}/files/content?path=${encodeURIComponent(path)}`
    )
  }

  const downloadProjectFileUrl = (path: string): string => {
    const projectDir = encodeURIComponent(currentProject.value.project_dir)
    return `${API_BASE}/api/projects/${projectDir}/files/download?path=${encodeURIComponent(path)}`
  }

  const deleteProjectFiles = (paths: string[]) => {
    const projectDir = encodeURIComponent(currentProject.value.project_dir)
    return request<{ deleted: string[]; errors: { path: string; error: string }[] }>(
      `/api/projects/${projectDir}/files/delete`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paths }),
      }
    )
  }

  // Schedules
  const getSchedules = () => request<ScheduleInfo[]>(withProject('/api/schedules'))
  const getSchedule = (id: string) => request<ScheduleInfo>(`/api/schedules/${id}`)
  const createSchedule = (data: CreateScheduleRequest) =>
    request<ScheduleInfo>(withProject('/api/schedules'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
  const updateSchedule = (id: string, data: UpdateScheduleRequest) =>
    request<ScheduleInfo>(`/api/schedules/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
  const deleteSchedule = (id: string) =>
    request<{ status: string; schedule_id: string }>(`/api/schedules/${id}`, { method: 'DELETE' })
  const toggleSchedule = (id: string) =>
    request<ScheduleInfo>(`/api/schedules/${id}/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })

  return {
    getAgents,
    getAgent,
    getAgentDetail,
    createAgent,
    updateAgent,
    deleteAgent,
    cloneAgent,
    runAgent,
    stopAllAgents,
    stopAgentTree,
    getTools,
    getToolIconUrl,
    getExecutions,
    getExecution,
    getExecutionTree,
    getExecutionLog,
    getExecutionTools,
    deleteExecution,
    getExecutionGraph,
    resetGraphEtag,
    getGraphDelta,
    resetGraphSequence,
    getGraphLayout,
    putGraphLayout,
    deleteGraphLayout,
    getProjects,
    createProject,
    cloneProject,
    deleteProject,
    getSchedules,
    getSchedule,
    createSchedule,
    updateSchedule,
    deleteSchedule,
    toggleSchedule,
    listProjectFiles,
    uploadProjectFile,
    getProjectFileContent,
    downloadProjectFileUrl,
    deleteProjectFiles,
  }
}
