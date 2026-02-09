export interface AgentInfo {
  name: string
  description: string
  tools: string[]
}

export interface AgentDetail {
  name: string
  description: string
  system_prompt: string
  tools: string[]
}

export interface CreateAgentRequest {
  name: string
  description: string
  system_prompt: string
  tools: string[]
}

export interface UpdateAgentRequest {
  description: string
  system_prompt: string
  tools: string[]
}

export interface RunAgentRequest {
  agent_name: string
  message: string
}

export interface RunAgentResponse {
  agent_id: string
  agent_name: string
  status: string
  message: string
}

export interface StopAllResponse {
  stopped_count: number
  agent_ids: string[]
  message: string
}

export interface ToolInfo {
  name: string
  description: string
}
