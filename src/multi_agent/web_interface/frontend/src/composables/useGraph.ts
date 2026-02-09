import { ref, type Ref } from 'vue'
import { Network, DataSet } from 'vis-network/standalone'
import type { GraphData, GraphNode, GraphStats } from '@/types/graph'
import { useApi } from './useApi'

const LAYOUT_STORAGE_KEY = 'agentGraphLayoutType'
const LAYOUT_PHYSICS = 'physics'
const LAYOUT_HIERARCHICAL = 'hierarchical'

export function useGraph() {
  const api = useApi()

  let network: Network | null = null
  let nodes: DataSet<any> | null = null
  let edges: DataSet<any> | null = null
  let updateInterval: ReturnType<typeof setInterval> | null = null
  let animationPhase = 0
  let animationFrameCount = 0
  const runningNodeIds = new Set<string>()

  const currentAgentId = ref<string | null>(null)
  const stats = ref<GraphStats>({
    totalNodes: 0,
    agents: 0,
    tools: 0,
    running: 0,
    completed: 0,
    totalErrors: 0,
  })
  const layoutType = ref(localStorage.getItem(LAYOUT_STORAGE_KEY) || LAYOUT_PHYSICS)
  const physicsEnabled = ref(true)

  function getGraphOptions(layout: string) {
    const baseOptions = {
      nodes: {
        font: { size: 14, color: '#e0c8a8', face: 'monospace' },
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
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        zoomView: true,
        dragView: true,
      },
    } as any

    if (layout === LAYOUT_HIERARCHICAL) {
      return {
        ...baseOptions,
        edges: {
          ...baseOptions.edges,
          smooth: { type: 'cubicBezier', forceDirection: 'vertical', roundness: 0.4 },
        },
        layout: {
          hierarchical: {
            enabled: true,
            direction: 'UD',
            sortMethod: 'directed',
            nodeSpacing: 150,
            levelSeparation: 150,
            shakeTowards: 'roots',
          },
        },
        physics: {
          enabled: true,
          hierarchicalRepulsion: {
            centralGravity: 0.0,
            springLength: 200,
            springConstant: 0.01,
            nodeDistance: 150,
            damping: 0.09,
          },
          solver: 'hierarchicalRepulsion',
        },
      }
    }

    return {
      ...baseOptions,
      edges: {
        ...baseOptions.edges,
        smooth: { type: 'continuous', roundness: 0.5 },
      },
      layout: { hierarchical: { enabled: false } },
      physics: {
        enabled: true,
        barnesHut: {
          gravitationalConstant: -10000,
          centralGravity: 0.3,
          springLength: 150,
          springConstant: 0.04,
          damping: 0.09,
          avoidOverlap: 1,
        },
        solver: 'barnesHut',
        stabilization: { enabled: true, iterations: 200, updateInterval: 25 },
      },
    }
  }

  function getPulsatingShadowSize(): number {
    return 20 + Math.sin(animationPhase) * 5
  }

  function initializeGraph(agentId: string, container: HTMLElement, onNodeClick?: (nodeId: string) => void) {
    currentAgentId.value = agentId
    nodes = new DataSet([])
    edges = new DataSet([])
    container.innerHTML = ''

    const options = getGraphOptions(layoutType.value)
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

    loadGraphData()
    startAutoRefresh()
  }

  async function loadGraphData() {
    if (!currentAgentId.value || !nodes || !edges) return

    try {
      const graphData = await api.getExecutionGraph(currentAgentId.value)

      // Update nodes
      const existingNodeIds = nodes.getIds() as string[]
      const newNodeIds = graphData.nodes.map((n) => n.id)
      const nodesToRemove = existingNodeIds.filter((id) => !newNodeIds.includes(id))
      if (nodesToRemove.length > 0) nodes.remove(nodesToRemove)

      runningNodeIds.clear()

      graphData.nodes.forEach((node) => {
        if (node.is_running) runningNodeIds.add(node.id)

        let borderColor = '#6b4030'
        let borderWidth = 2
        let shadowConfig = {
          enabled: true,
          color: 'rgba(180, 100, 50, 0.4)',
          size: 15,
          x: 0,
          y: 0,
        }

        if (node.is_running) {
          const pulsatingSize = getPulsatingShadowSize()
          borderWidth = 4
          if (node.current_state === 'generating') {
            borderColor = '#e89030'
            shadowConfig = { enabled: true, color: 'rgba(232, 144, 48, 0.7)', size: pulsatingSize, x: 0, y: 0 }
          } else if (node.current_state === 'waiting') {
            borderColor = '#a06850'
            shadowConfig = { enabled: true, color: 'rgba(160, 104, 80, 0.6)', size: pulsatingSize, x: 0, y: 0 }
          } else if (node.current_state === 'executing_tool') {
            borderColor = '#c89838'
            shadowConfig = { enabled: true, color: 'rgba(200, 152, 56, 0.7)', size: pulsatingSize, x: 0, y: 0 }
          } else {
            borderColor = '#d0b880'
            shadowConfig = { enabled: true, color: 'rgba(208, 184, 128, 0.6)', size: pulsatingSize, x: 0, y: 0 }
          }
        }

        if (node.error_count > 0 && !node.is_running) {
          borderColor = '#c03030'
          borderWidth = 3
          shadowConfig = { enabled: true, color: 'rgba(192, 48, 48, 0.6)', size: 18, x: 0, y: 0 }
        } else if (node.error_count > 0 && node.is_running) {
          borderColor = '#d04030'
          shadowConfig.color = 'rgba(208, 64, 48, 0.7)'
        }

        let enhancedLabel = node.label
        if (node.is_running && node.current_state && node.group !== 'tool') {
          const indicators: Record<string, string> = {
            generating: '⚡',
            waiting: '⏳',
            executing_tool: '🔧',
          }
          const indicator = indicators[node.current_state] || ''
          if (indicator) enhancedLabel = `${indicator} ${node.label}`
        }
        if (node.error_count > 0) {
          enhancedLabel = `⚠️ ${node.error_count}\n${enhancedLabel}`
        }

        const visNode = {
          id: node.id,
          label: enhancedLabel,
          group: node.group,
          color: {
            background: node.color,
            border: borderColor,
            highlight: { background: node.color, border: '#f0d8b0' },
          },
          borderWidth,
          shadow: shadowConfig,
          shape: node.shape,
          size: node.size,
          title: node.error_count > 0
            ? `${node.label}\n⚠️ ${node.error_count} error${node.error_count > 1 ? 's' : ''}`
            : node.label,
        }

        if (nodes!.get(node.id)) {
          nodes!.update(visNode)
        } else {
          nodes!.add(visNode)
        }
      })

      // Update edges
      const existingEdgeIds = edges.getIds() as string[]
      const newEdgeIds = graphData.edges.map((e) => e.id)
      const edgesToRemove = existingEdgeIds.filter((id) => !newEdgeIds.includes(id))
      if (edgesToRemove.length > 0) edges.remove(edgesToRemove)

      graphData.edges.forEach((edge) => {
        const isAsync = edge.call_mode === 'asynchronous'
        const visEdge = {
          id: edge.id,
          from: edge.from_node,
          to: edge.to_node,
          dashes: isAsync,
          width: isAsync ? 2 : 3,
          color: {
            color: isAsync ? '#7a5840' : '#5a3a28',
            highlight: isAsync ? '#a07858' : '#8a6048',
          },
          title: `${isAsync ? 'Asynchronous' : 'Synchronous'} call`,
        }

        if (edges!.get(edge.id)) {
          edges!.update(visEdge)
        } else {
          edges!.add(visEdge)
        }
      })

      // Update stats
      updateStats(graphData)
    } catch (error) {
      console.error('Failed to load graph data:', error)
    }
  }

  function updateStats(graphData: GraphData) {
    stats.value = {
      totalNodes: graphData.nodes.length,
      agents: graphData.nodes.filter((n) => n.group === 'agent' || n.group === 'root').length,
      tools: graphData.nodes.filter((n) => n.group === 'tool').length,
      running: graphData.nodes.filter((n) => n.is_running).length,
      completed: graphData.nodes.filter((n) => !n.is_running).length,
      totalErrors: graphData.nodes.reduce((sum, n) => sum + (n.error_count || 0), 0),
    }
  }

  function updateRunningShadows() {
    if (!nodes || runningNodeIds.size === 0) return
    const pulsatingSize = getPulsatingShadowSize()
    runningNodeIds.forEach((nodeId) => {
      const node = nodes!.get(nodeId)
      if (node?.shadow?.size > 15) {
        nodes!.update({
          id: nodeId,
          shadow: { ...node.shadow, size: pulsatingSize },
        })
      }
    })
  }

  function updateAnimation() {
    animationPhase += 0.15
    animationFrameCount++
    if (animationFrameCount >= 10) {
      animationFrameCount = 0
      loadGraphData()
    } else {
      updateRunningShadows()
    }
  }

  function startAutoRefresh() {
    stopAutoRefresh()
    updateInterval = setInterval(updateAnimation, 100)
  }

  function stopAutoRefresh() {
    if (updateInterval) {
      clearInterval(updateInterval)
      updateInterval = null
    }
  }

  function cleanup() {
    stopAutoRefresh()
    if (network) {
      network.destroy()
      network = null
    }
    nodes = null
    edges = null
    currentAgentId.value = null
    animationPhase = 0
    animationFrameCount = 0
    runningNodeIds.clear()
  }

  function fitView() {
    network?.fit({ animation: { duration: 1000, easingFunction: 'easeInOutQuad' } })
  }

  function resetPhysics() {
    network?.stabilize()
  }

  function togglePhysics() {
    if (!network) return
    physicsEnabled.value = !physicsEnabled.value
    network.setOptions({ physics: { enabled: physicsEnabled.value } })
  }

  function toggleLayout() {
    if (!network) return
    const newLayout = layoutType.value === LAYOUT_PHYSICS ? LAYOUT_HIERARCHICAL : LAYOUT_PHYSICS
    layoutType.value = newLayout
    localStorage.setItem(LAYOUT_STORAGE_KEY, newLayout)
    network.setOptions(getGraphOptions(newLayout))
    setTimeout(() => {
      network?.stabilize()
      network?.fit()
    }, 100)
  }

  function exportImage() {
    if (!network) return
    const canvas = (network as any).canvas.frame.canvas as HTMLCanvasElement
    const dataURL = canvas.toDataURL('image/png')
    const link = document.createElement('a')
    link.download = `agent-graph-${currentAgentId.value}.png`
    link.href = dataURL
    link.click()
  }

  function getNodeGroup(nodeId: string): string | null {
    if (!nodes) return null
    const node = nodes.get(nodeId)
    return node?.group || null
  }

  function getParentAgentId(toolNodeId: string): string | null {
    if (!edges) return null
    const edgeIds = edges.getIds() as string[]
    for (const edgeId of edgeIds) {
      const edge = edges.get(edgeId)
      if (edge?.to === toolNodeId) return edge.from
    }
    return null
  }

  return {
    currentAgentId,
    stats,
    layoutType,
    physicsEnabled,
    initializeGraph,
    loadGraphData,
    cleanup,
    fitView,
    resetPhysics,
    togglePhysics,
    toggleLayout,
    exportImage,
    getNodeGroup,
    getParentAgentId,
  }
}
