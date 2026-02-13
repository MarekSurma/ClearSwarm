import { ref } from 'vue'
import { Network, DataSet } from 'vis-network/standalone'
import { useApi } from './useApi'
import type { AgentDetail, ToolInfo } from '@/types/agent'

interface VisNode {
  id: string
  label: string
  shape: string
  color: { background: string; border: string; highlight: { background: string; border: string } }
  size: number
  borderWidth: number
  shadow: { enabled: boolean; color: string; size: number; x: number; y: number }
  font: { size: number; color: string }
}

interface VisEdge {
  id: string
  from: string
  to: string
}

export function useVisualGraph() {
  const api = useApi()

  let network: Network | null = null
  let nodes: DataSet<VisNode> | null = null
  let edges: DataSet<VisEdge> | null = null

  const isLoading = ref(false)

  // Cache for agent details to avoid redundant API calls
  const agentCache = new Map<string, AgentDetail>()
  const toolCache = new Map<string, ToolInfo>()

  async function initialize(container: HTMLElement, onNodeClick?: (nodeId: string) => void) {
    nodes = new DataSet([])
    edges = new DataSet([])
    container.innerHTML = ''

    const options = {
      nodes: {
        font: { size: 14, color: '#e0c8a8', face: 'Inter, sans-serif' },
        borderWidth: 2,
        shadow: {
          enabled: true,
          color: 'rgba(180, 100, 50, 0.35)',
          size: 12,
          x: 0,
          y: 0,
        },
      },
      edges: {
        width: 2,
        color: { color: '#5a3a28', highlight: '#8a6048', hover: '#8a6048' },
        arrows: { to: { enabled: true, scaleFactor: 0.5 } },
        smooth: { type: 'continuous', roundness: 0.5 },
      },
      layout: {
        hierarchical: {
          enabled: true,
          direction: 'UD',
          sortMethod: 'directed',
          nodeSpacing: 150,
          levelSeparation: 120,
          shakeTowards: 'roots',
        },
      },
      physics: {
        enabled: true,
        hierarchicalRepulsion: {
          centralGravity: 0.0,
          springLength: 180,
          springConstant: 0.01,
          nodeDistance: 120,
          damping: 0.09,
        },
        solver: 'hierarchicalRepulsion',
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        zoomView: true,
        dragView: true,
      },
    }

    network = new Network(container, { nodes, edges }, options)

    network.on('click', (params: any) => {
      if (params.nodes.length > 0 && onNodeClick) {
        onNodeClick(params.nodes[0])
      }
    })

    network.on('hoverNode', () => {
      container.style.cursor = 'pointer'
    })

    network.on('blurNode', () => {
      container.style.cursor = 'default'
    })
  }

  async function loadToolsCache() {
    if (toolCache.size > 0) return
    try {
      const tools = await api.getTools()
      tools.forEach((tool) => {
        toolCache.set(tool.name, tool)
      })
    } catch (error) {
      console.error('Failed to load tools:', error)
    }
  }

  async function buildGraphForAgent(rootAgentName: string, allAgents: string[]) {
    if (!nodes || !edges) return

    isLoading.value = true
    agentCache.clear()

    try {
      // Load tools cache first
      await loadToolsCache()

      // Clear existing graph
      nodes.clear()
      edges.clear()

      // BFS to build the graph
      const visited = new Set<string>()
      const queue: Array<{ agentName: string; isRoot: boolean }> = [{ agentName: rootAgentName, isRoot: true }]

      while (queue.length > 0) {
        const { agentName, isRoot } = queue.shift()!

        // Skip if already visited
        if (visited.has(agentName)) continue
        visited.add(agentName)

        // Fetch agent detail
        let agentDetail: AgentDetail
        if (agentCache.has(agentName)) {
          agentDetail = agentCache.get(agentName)!
        } else {
          try {
            agentDetail = await api.getAgentDetail(agentName)
            agentCache.set(agentName, agentDetail)
          } catch (error) {
            console.error(`Failed to load agent ${agentName}:`, error)
            continue
          }
        }

        // Add agent node
        const agentNodeId = `agent::${agentName}`
        if (!nodes.get(agentNodeId)) {
          nodes.add({
            id: agentNodeId,
            label: agentName,
            shape: 'box',
            color: {
              background: '#e89030',
              border: '#c07020',
              highlight: { background: '#f0a040', border: '#d08030' },
            },
            size: isRoot ? 30 : 20,
            borderWidth: isRoot ? 3 : 2,
            shadow: {
              enabled: true,
              color: isRoot ? 'rgba(232, 144, 48, 0.5)' : 'rgba(232, 144, 48, 0.35)',
              size: isRoot ? 18 : 12,
              x: 0,
              y: 0,
            },
            font: { size: isRoot ? 16 : 14, color: '#e0c8a8' },
          })
        }

        // Process tools and sub-agents
        agentDetail.tools.forEach((toolOrAgent) => {
          const isAgent = allAgents.includes(toolOrAgent)

          if (isAgent) {
            // Sub-agent
            const subAgentNodeId = `agent::${toolOrAgent}`

            // Add edge
            const edgeId = `${agentNodeId}->agent::${toolOrAgent}`
            if (!edges.get(edgeId)) {
              edges.add({
                id: edgeId,
                from: agentNodeId,
                to: subAgentNodeId,
              })
            }

            // Queue sub-agent for processing (if not already visited)
            if (!visited.has(toolOrAgent)) {
              queue.push({ agentName: toolOrAgent, isRoot: false })
            }
          } else {
            // Tool node (create unique ID per parent)
            const toolNodeId = `tool::${toolOrAgent}::from::${agentName}`
            const toolInfo = toolCache.get(toolOrAgent)

            if (!nodes.get(toolNodeId)) {
              nodes.add({
                id: toolNodeId,
                label: toolOrAgent,
                shape: 'ellipse',
                color: {
                  background: '#5a9560',
                  border: '#4a7850',
                  highlight: { background: '#6aaf70', border: '#5a9560' },
                },
                size: 15,
                borderWidth: 2,
                shadow: {
                  enabled: true,
                  color: 'rgba(90, 149, 96, 0.35)',
                  size: 10,
                  x: 0,
                  y: 0,
                },
                font: { size: 12, color: '#e0c8a8' },
              })
            }

            // Add edge
            const edgeId = `${agentNodeId}->${toolNodeId}`
            if (!edges.get(edgeId)) {
              edges.add({
                id: edgeId,
                from: agentNodeId,
                to: toolNodeId,
              })
            }
          }
        })
      }

      // Fit view after building
      fitView()
    } finally {
      isLoading.value = false
    }
  }

  function cleanup() {
    if (network) {
      network.destroy()
      network = null
    }
    nodes = null
    edges = null
    agentCache.clear()
  }

  function fitView() {
    if (network) {
      setTimeout(() => {
        network?.fit({ animation: { duration: 800, easingFunction: 'easeInOutQuad' } })
      }, 100)
    }
  }

  function getParentAgents(nodeId: string): string[] {
    if (!edges) return []

    const parents: string[] = []

    // Check if this is a tool node
    if (nodeId.startsWith('tool::')) {
      // Extract tool name and parent from ID format: tool::toolName::from::parentAgent
      const match = nodeId.match(/^tool::(.+?)::from::(.+)$/)
      if (match) {
        parents.push(match[2])
      }
    }

    // For agent nodes, find all agents that reference this agent
    if (nodeId.startsWith('agent::')) {
      const agentName = nodeId.replace('agent::', '')
      const allEdges = edges.getIds()

      allEdges.forEach((edgeId) => {
        const edge = edges!.get(edgeId as string)
        if (edge && edge.to === nodeId) {
          // Extract parent agent name from the 'from' node
          const parentNodeId = edge.from
          if (parentNodeId.startsWith('agent::')) {
            parents.push(parentNodeId.replace('agent::', ''))
          }
        }
      })
    }

    return parents
  }

  return {
    isLoading,
    initialize,
    buildGraphForAgent,
    cleanup,
    fitView,
    getParentAgents,
  }
}
