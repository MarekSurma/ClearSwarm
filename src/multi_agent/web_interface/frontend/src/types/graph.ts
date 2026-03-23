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

export interface GraphChange {
  sequence: number
  change_type: 'node_add' | 'node_update' | 'node_remove' | 'edge_add' | 'edge_update' | 'edge_remove'
  entity_id: string
  data: GraphNode | GraphEdge | null
}

export interface GraphDeltaResponse {
  type: 'delta'
  current_sequence: number
  changes: GraphChange[]
}

export interface GraphSnapshotResponse {
  type: 'snapshot'
  current_sequence: number
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export type GraphResponse = GraphDeltaResponse | GraphSnapshotResponse
