export interface WSExecution {
  agent_id: string
  agent_name: string
  parent_agent_id: string | null
  started_at: string
  completed_at: string | null
  current_state: string
  is_running: boolean
}

export interface WSInitialState {
  type: 'initial_state'
  executions: WSExecution[]
}

export interface WSExecutionsUpdate {
  type: 'executions_update'
  executions: WSExecution[]
}

export interface WSRunningAgents {
  type: 'running_agents'
  count: number
  agents: { agent_id: string; agent_name: string; current_state: string }[]
}

export interface WSAgentCompleted {
  type: 'agent_completed'
  agent_id: string
  final_response?: string
  total_iterations?: number
}

export interface WSAgentState {
  type: 'agent_state'
  agent_id: string
}

export interface WSAgentUpdate {
  type: 'agent_update'
  agent_id: string
}

export interface WSError {
  type: 'error'
  message: string
}

export type WebSocketMessage =
  | WSInitialState
  | WSExecutionsUpdate
  | WSRunningAgents
  | WSAgentCompleted
  | WSAgentState
  | WSAgentUpdate
  | WSError
