import { ref } from 'vue'
import { Network, DataSet } from 'vis-network/standalone'
import { useApi } from './useApi'
import type { AgentDetail, ToolInfo } from '@/types/agent'
import { GRAPH_COLORS } from '@/config/graphColors'

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

  async function initialize(container: HTMLElement, onNodeClick?: (nodeId: string) => void, onBackgroundClick?: () => void) {
    nodes = new DataSet([])
    edges = new DataSet([])
    container.innerHTML = ''

    const options = {
      nodes: {
        font: { size: 14, color: GRAPH_COLORS.font.primary, face: GRAPH_COLORS.font.face },
        borderWidth: 2,
        shadow: {
          enabled: true,
          color: GRAPH_COLORS.shadows.default,
          size: GRAPH_COLORS.shadows.defaultSize,
          x: 0,
          y: 0,
        },
      },
      edges: {
        width: 2,
        color: {
          color: GRAPH_COLORS.edges.default,
          highlight: GRAPH_COLORS.edges.highlight,
          hover: GRAPH_COLORS.edges.hover,
        },
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
      } else if (params.nodes.length === 0 && onBackgroundClick) {
        onBackgroundClick()
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
              background: GRAPH_COLORS.agent.background,
              border: GRAPH_COLORS.agent.border,
              highlight: {
                background: GRAPH_COLORS.agent.highlightBackground,
                border: GRAPH_COLORS.agent.highlightBorder,
              },
            },
            size: isRoot ? 30 : 20,
            borderWidth: isRoot ? 3 : 2,
            shadow: {
              enabled: true,
              color: isRoot ? GRAPH_COLORS.agent.rootShadow : GRAPH_COLORS.agent.shadow,
              size: isRoot ? GRAPH_COLORS.agent.rootShadowSize : GRAPH_COLORS.agent.shadowSize,
              x: 0,
              y: 0,
            },
            font: { size: isRoot ? 16 : 14, color: GRAPH_COLORS.font.primary },
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
                  background: GRAPH_COLORS.tool.background,
                  border: GRAPH_COLORS.tool.border,
                  highlight: {
                    background: GRAPH_COLORS.tool.highlightBackground,
                    border: GRAPH_COLORS.tool.highlightBorder,
                  },
                },
                size: 15,
                borderWidth: 2,
                shadow: {
                  enabled: true,
                  color: GRAPH_COLORS.tool.shadow,
                  size: GRAPH_COLORS.tool.shadowSize,
                  x: 0,
                  y: 0,
                },
                font: { size: 12, color: GRAPH_COLORS.font.primary },
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

  function addToolNode(parentAgentName: string, toolName: string) {
    if (!nodes || !edges) return

    const parentNodeId = `agent::${parentAgentName}`
    const toolNodeId = `tool::${toolName}::from::${parentAgentName}`

    if (!nodes.get(toolNodeId)) {
      nodes.add({
        id: toolNodeId,
        label: toolName,
        shape: 'ellipse',
        color: {
          background: GRAPH_COLORS.tool.background,
          border: GRAPH_COLORS.tool.border,
          highlight: {
            background: GRAPH_COLORS.tool.highlightBackground,
            border: GRAPH_COLORS.tool.highlightBorder,
          },
        },
        size: 15,
        borderWidth: 2,
        shadow: {
          enabled: true,
          color: GRAPH_COLORS.tool.shadow,
          size: GRAPH_COLORS.tool.shadowSize,
          x: 0,
          y: 0,
        },
        font: { size: 12, color: GRAPH_COLORS.font.primary },
      })
    }

    const edgeId = `${parentNodeId}->${toolNodeId}`
    if (!edges.get(edgeId)) {
      edges.add({ id: edgeId, from: parentNodeId, to: toolNodeId })
    }
  }

  async function addSubAgentNode(parentAgentName: string, subAgentName: string, allAgents: string[]) {
    if (!nodes || !edges) return

    const parentNodeId = `agent::${parentAgentName}`
    const subAgentNodeId = `agent::${subAgentName}`

    // Add edge first
    const edgeId = `${parentNodeId}->${subAgentNodeId}`
    if (!edges.get(edgeId)) {
      edges.add({ id: edgeId, from: parentNodeId, to: subAgentNodeId })
    }

    // If agent node already exists, just the edge is enough
    if (nodes.get(subAgentNodeId)) return

    // BFS expand the new sub-agent and its children
    const visited = new Set<string>()
    // Collect already-present agent nodes to avoid re-expanding
    nodes.getIds().forEach((id) => {
      const s = id as string
      if (s.startsWith('agent::')) visited.add(s.replace('agent::', ''))
    })
    // But allow the new sub-agent itself to be processed
    visited.delete(subAgentName)

    const queue = [subAgentName]

    while (queue.length > 0) {
      const agentName = queue.shift()!
      if (visited.has(agentName)) continue
      visited.add(agentName)

      let agentDetail: AgentDetail
      try {
        agentDetail = await api.getAgentDetail(agentName)
        agentCache.set(agentName, agentDetail)
      } catch { continue }

      const agentNodeId = `agent::${agentName}`
      if (!nodes.get(agentNodeId)) {
        nodes.add({
          id: agentNodeId,
          label: agentName,
          shape: 'box',
          color: {
            background: GRAPH_COLORS.agent.background,
            border: GRAPH_COLORS.agent.border,
            highlight: {
              background: GRAPH_COLORS.agent.highlightBackground,
              border: GRAPH_COLORS.agent.highlightBorder,
            },
          },
          size: 20,
          borderWidth: 2,
          shadow: {
            enabled: true,
            color: GRAPH_COLORS.agent.shadow,
            size: GRAPH_COLORS.agent.shadowSize,
            x: 0,
            y: 0,
          },
          font: { size: 14, color: GRAPH_COLORS.font.primary },
        })
      }

      agentDetail.tools.forEach((toolOrAgent) => {
        if (allAgents.includes(toolOrAgent)) {
          const childEdgeId = `${agentNodeId}->agent::${toolOrAgent}`
          if (!edges!.get(childEdgeId)) {
            edges!.add({ id: childEdgeId, from: agentNodeId, to: `agent::${toolOrAgent}` })
          }
          if (!visited.has(toolOrAgent)) queue.push(toolOrAgent)
        } else {
          addToolNode(agentName, toolOrAgent)
        }
      })
    }
  }

  function removeNode(nodeId: string) {
    if (!nodes || !edges) return

    if (nodeId.startsWith('tool::')) {
      // Tool nodes: remove the node and its incoming edge
      const allEdges = edges.get() as VisEdge[]
      const toRemove = allEdges.filter((e) => e.to === nodeId).map((e) => e.id)
      edges.remove(toRemove)
      nodes.remove(nodeId)
    } else if (nodeId.startsWith('agent::')) {
      // Agent nodes: remove the incoming edge(s) that were severed.
      // If the node has no remaining incoming edges, remove it and its orphaned children.
      removeOrphanedSubtree(nodeId)
    }
  }

  function removeEdgeFromParent(nodeId: string, parentAgentName: string) {
    if (!edges) return

    const parentNodeId = `agent::${parentAgentName}`
    const allEdges = edges.get() as VisEdge[]
    const edgeToRemove = allEdges.find((e) => e.from === parentNodeId && e.to === nodeId)
    if (edgeToRemove) {
      edges.remove(edgeToRemove.id)
    }

    // For tool nodes, always remove the node (they're unique per parent)
    if (nodeId.startsWith('tool::') && nodes) {
      nodes.remove(nodeId)
      return
    }

    // For agent nodes, check if any incoming edges remain
    if (nodeId.startsWith('agent::')) {
      removeOrphanedSubtree(nodeId)
    }
  }

  function removeOrphanedSubtree(nodeId: string) {
    if (!nodes || !edges) return

    const allEdges = edges.get() as VisEdge[]
    const hasIncoming = allEdges.some((e) => e.to === nodeId)
    if (hasIncoming) return // Still referenced by another parent

    // BFS remove this node and orphaned children
    const queue = [nodeId]
    while (queue.length > 0) {
      const id = queue.shift()!

      // Find outgoing edges and queue children
      const outgoing = (edges.get() as VisEdge[]).filter((e) => e.from === id)
      outgoing.forEach((e) => {
        edges!.remove(e.id)
        // Check if child has other incoming edges
        const childIncoming = (edges!.get() as VisEdge[]).some((e2) => e2.to === e.to)
        if (!childIncoming) {
          queue.push(e.to)
        }
      })

      // Remove any remaining incoming edges and the node itself
      const incoming = (edges.get() as VisEdge[]).filter((e) => e.to === id)
      edges.remove(incoming.map((e) => e.id))
      nodes.remove(id)
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
    addToolNode,
    addSubAgentNode,
    removeEdgeFromParent,
  }
}
