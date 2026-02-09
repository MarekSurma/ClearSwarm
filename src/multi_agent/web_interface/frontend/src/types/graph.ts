export interface GraphNode {
  id: string
  label: string
  group: 'root' | 'agent' | 'tool'
  color: string
  shape: string
  size: number
  is_running: boolean
  current_state: string | null
  error_count: number
}

export interface GraphEdge {
  id: string
  from_node: string
  to_node: string
  dashes: boolean
  call_mode: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface GraphStats {
  totalNodes: number
  agents: number
  tools: number
  running: number
  completed: number
  totalErrors: number
}
