export interface AgentExecution {
  agent_id: string
  agent_name: string
  parent_agent_id: string | null
  parent_agent_name: string
  started_at: string
  completed_at: string | null
  current_state: string
  call_mode: string
  is_running: boolean
  log_file: string | null
}

export interface ToolExecution {
  tool_execution_id: string
  tool_name: string
  parameters: Record<string, unknown>
  call_mode: string
  started_at: string
  completed_at: string | null
  result: string | null
  is_running: boolean
}

export interface ExecutionTree {
  agent_id: string
  agent_name: string
  parent_agent_id: string | null
  started_at: string
  completed_at: string | null
  current_state: string
  is_running: boolean
  children: ExecutionTree[]
  tools: ToolExecution[]
}

export interface ExecutionLog {
  agent_id: string
  agent_name: string
  parent_agent_id: string | null
  parent_agent_name: string
  started_at: string
  completed_at: string | null
  final_response: string | null
  total_iterations: number | null
  session_ended_explicitly: boolean | null
  interactions: LogMessage[]
}

export interface LogMessage {
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  timestamp?: string
}
