import { ref, type Ref } from 'vue'
import { Network, DataSet } from 'vis-network/standalone'
import type { GraphData, GraphNode, GraphEdge, GraphChange, GraphStats } from '@/types/graph'
import { useApi } from './useApi'
import { GRAPH_COLORS } from '@/config/graphColors'

const LAYOUT_STORAGE_KEY = 'agentGraphLayoutType'
const LAYOUT_PHYSICS = 'physics'
const LAYOUT_HIERARCHICAL = 'hierarchical'

export function useGraph() {
  const api = useApi()

  let network: Network | null = null
  let nodes: DataSet<any> | null = null
  let edges: DataSet<any> | null = null
  let animationHandle: number | null = null
  let fetchInterval: ReturnType<typeof setInterval> | null = null
  let animationPhase = 0
  const runningNodeIds = new Set<string>()
  const graphNodeData = new Map<string, GraphNode>()

  const POLL_ACTIVE_MS = 2000   // 2s when agents are running
  const POLL_IDLE_MS = 10000    // 10s when everything completed
  const LARGE_GRAPH_THRESHOLD = 150  // disable physics above this

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
        font: { size: 14, color: GRAPH_COLORS.font.primary, face: GRAPH_COLORS.font.face },
        margin: { top: 6, right: 6, bottom: 6, left: 6 },
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
          color: GRAPH_COLORS.visualizer.edges.default,
          highlight: GRAPH_COLORS.visualizer.edges.highlight,
          hover: GRAPH_COLORS.visualizer.edges.hover,
        },
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

  function createNetwork(container: HTMLElement, graphOptions: any, onNodeClick?: (nodeId: string) => void) {
    // vis-network adds a non-passive wheel listener for zoom, which triggers a
    // Chrome warning.  The graph lives inside a fullscreen modal with no
    // scrollable parent, so making it passive is safe (preventDefault is a no-op
    // here anyway).
    const origAddEventListener = container.addEventListener
    container.addEventListener = function (
      type: string,
      listener: EventListenerOrEventListenerObject,
      options?: boolean | AddEventListenerOptions,
    ) {
      if (type === 'wheel' || type === 'mousewheel') {
        const opts = typeof options === 'object' ? { ...options, passive: true } : { passive: true }
        origAddEventListener.call(this, type, listener, opts)
      } else {
        origAddEventListener.call(this, type, listener, options)
      }
    } as typeof container.addEventListener

    network = new Network(container, { nodes: nodes!, edges: edges! }, graphOptions)

    // Restore original so future listeners on this element are unaffected
    container.addEventListener = origAddEventListener

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

  async function initializeGraph(agentId: string, container: HTMLElement, onNodeClick?: (nodeId: string) => void) {
    currentAgentId.value = agentId
    nodes = new DataSet([])
    edges = new DataSet([])
    graphNodeData.clear()
    container.innerHTML = ''

    api.resetGraphSequence()

    // Pre-fetch graph data to determine size before creating the network
    let graphData: GraphData | null = null
    try {
      const response = await api.getGraphDelta(agentId)
      if (response && response.type === 'snapshot') {
        graphData = { nodes: response.nodes, edges: response.edges }
      }
    } catch (error) {
      console.error('Failed to load initial graph data:', error)
    }

    // Choose layout based on graph size
    const nodeCount = graphData?.nodes?.length ?? 0
    const isLargeGraph = nodeCount > LARGE_GRAPH_THRESHOLD
    let graphOptions: any

    if (isLargeGraph) {
      // Large graph: use hierarchical layout with no physics to avoid freeze
      graphOptions = getGraphOptions(LAYOUT_HIERARCHICAL)
      graphOptions.physics = { enabled: false }
      physicsEnabled.value = false
    } else {
      graphOptions = getGraphOptions(layoutType.value)
    }

    createNetwork(container, graphOptions, onNodeClick)

    // Process the pre-fetched data
    if (graphData) {
      processGraphData(graphData)

      // Fit view after nodes are placed
      setTimeout(() => network?.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } }), 200)
    }

    // Only start auto-refresh if there are running agents
    if (stats.value.running > 0) {
      startAutoRefresh()
    }
  }

  function buildVisNode(node: GraphNode): any {
    let borderColor = GRAPH_COLORS.visualizer.borders.default
    let borderWidth = 2
    let shadowConfig = {
      enabled: true,
      color: GRAPH_COLORS.shadows.default,
      size: 15,
      x: 0,
      y: 0,
    }

    if (node.is_running) {
      const pulsatingSize = getPulsatingShadowSize()
      borderWidth = 4
      if (node.current_state === 'generating') {
        borderColor = GRAPH_COLORS.running.generating.border
        shadowConfig = { enabled: true, color: GRAPH_COLORS.running.generating.shadow, size: pulsatingSize, x: 0, y: 0 }
      } else if (node.current_state === 'waiting') {
        borderColor = GRAPH_COLORS.running.waiting.border
        shadowConfig = { enabled: true, color: GRAPH_COLORS.running.waiting.shadow, size: pulsatingSize, x: 0, y: 0 }
      } else if (node.current_state === 'executing_tool') {
        borderColor = GRAPH_COLORS.running.executingTool.border
        shadowConfig = { enabled: true, color: GRAPH_COLORS.running.executingTool.shadow, size: pulsatingSize, x: 0, y: 0 }
      } else {
        borderColor = GRAPH_COLORS.running.default.border
        shadowConfig = { enabled: true, color: GRAPH_COLORS.running.default.shadow, size: pulsatingSize, x: 0, y: 0 }
      }
    }

    if (node.error_count > 0 && !node.is_running) {
      borderColor = GRAPH_COLORS.error.border
      borderWidth = 3
      shadowConfig = { enabled: true, color: GRAPH_COLORS.error.shadow, size: GRAPH_COLORS.error.shadowSize, x: 0, y: 0 }
    } else if (node.error_count > 0 && node.is_running) {
      borderColor = GRAPH_COLORS.error.borderRunning
      shadowConfig.color = GRAPH_COLORS.error.shadowRunning
    }

    const groupConfig = node.group === 'root'
      ? GRAPH_COLORS.visualizer.root
      : node.group === 'tool'
        ? GRAPH_COLORS.visualizer.tool
        : GRAPH_COLORS.visualizer.agent
    const bgColor = node.is_running ? groupConfig.backgroundRunning : groupConfig.background

    let enhancedLabel = node.label
    if (node.is_running && node.current_state && node.group !== 'tool') {
      const indicators: Record<string, string> = { generating: '⚡', waiting: '⏳', executing_tool: '🔧' }
      const indicator = indicators[node.current_state] || ''
      if (indicator) enhancedLabel = `${indicator} ${node.label}`
    }
    if (node.error_count > 0) {
      enhancedLabel = `⚠️ ${node.error_count}\n${enhancedLabel}`
    }

    return {
      id: node.id,
      label: enhancedLabel,
      group: node.group,
      font: { color: groupConfig.font },
      color: {
        background: bgColor,
        border: borderColor,
        highlight: { background: bgColor, border: GRAPH_COLORS.visualizer.borders.highlight },
        hover: { background: bgColor, border: GRAPH_COLORS.visualizer.borders.highlight },
      },
      borderWidth,
      shadow: shadowConfig,
      shape: node.shape,
      size: node.size,
      title: node.error_count > 0
        ? `${node.label}\n⚠️ ${node.error_count} error${node.error_count > 1 ? 's' : ''}`
        : node.label,
    }
  }

  function buildVisEdge(edge: GraphEdge): any {
    const isAsync = edge.call_mode === 'asynchronous'
    return {
      id: edge.id,
      from: edge.from_node,
      to: edge.to_node,
      dashes: isAsync,
      width: isAsync ? 2 : 3,
      color: {
        color: isAsync ? GRAPH_COLORS.visualizer.edges.async : GRAPH_COLORS.visualizer.edges.default,
        highlight: isAsync ? GRAPH_COLORS.visualizer.edges.asyncHighlight : GRAPH_COLORS.visualizer.edges.highlight,
      },
      title: `${isAsync ? 'Asynchronous' : 'Synchronous'} call`,
    }
  }

  function processGraphData(graphData: GraphData) {
    if (!nodes || !edges) return

    // Remove obsolete nodes
    const existingNodeIds = nodes.getIds() as string[]
    const newNodeIds = graphData.nodes.map((n) => n.id)
    const nodesToRemove = existingNodeIds.filter((id) => !newNodeIds.includes(id))
    if (nodesToRemove.length > 0) {
      nodes.remove(nodesToRemove)
      nodesToRemove.forEach((id) => graphNodeData.delete(id))
    }

    runningNodeIds.clear()

    graphData.nodes.forEach((node) => {
      graphNodeData.set(node.id, node)
      if (node.is_running) runningNodeIds.add(node.id)
      const visNode = buildVisNode(node)
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
      const visEdge = buildVisEdge(edge)
      if (edges!.get(edge.id)) {
        edges!.update(visEdge)
      } else {
        edges!.add(visEdge)
      }
    })

    updateStats(graphData)
  }

  function applyDelta(changes: GraphChange[]) {
    if (!nodes || !edges) return

    for (const change of changes) {
      switch (change.change_type) {
        case 'node_add':
        case 'node_update': {
          const nodeData = change.data as GraphNode
          graphNodeData.set(nodeData.id, nodeData)
          if (nodeData.is_running) runningNodeIds.add(nodeData.id)
          else runningNodeIds.delete(nodeData.id)
          const visNode = buildVisNode(nodeData)
          if (nodes!.get(nodeData.id)) nodes!.update(visNode)
          else nodes!.add(visNode)
          break
        }
        case 'node_remove':
          nodes!.remove(change.entity_id)
          runningNodeIds.delete(change.entity_id)
          graphNodeData.delete(change.entity_id)
          break
        case 'edge_add':
        case 'edge_update': {
          const edgeData = change.data as GraphEdge
          const visEdge = buildVisEdge(edgeData)
          if (edges!.get(edgeData.id)) edges!.update(visEdge)
          else edges!.add(visEdge)
          break
        }
        case 'edge_remove':
          edges!.remove(change.entity_id)
          break
      }
    }

    recalculateStats()
  }

  async function loadGraphData(retries = 1) {
    if (!currentAgentId.value || !nodes || !edges) return

    try {
      const response = await api.getGraphDelta(currentAgentId.value)

      // Server returned 304 Not Modified — nothing changed
      if (!response) return

      const wasRunning = stats.value.running > 0

      if (response.type === 'snapshot') {
        processGraphData({ nodes: response.nodes, edges: response.edges })
      } else {
        applyDelta(response.changes)
      }

      const isNowRunning = stats.value.running > 0

      if (wasRunning && !isNowRunning) {
        stopAutoRefresh()
      } else if (!wasRunning && isNowRunning) {
        startAutoRefresh()
      } else if (wasRunning && isNowRunning) {
        adjustPollingInterval()
      }
    } catch (error) {
      if (retries > 0) {
        setTimeout(() => loadGraphData(retries - 1), 1000)
      } else {
        console.error('Failed to load graph data:', error)
      }
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

  function recalculateStats() {
    const allNodes = Array.from(graphNodeData.values())
    stats.value = {
      totalNodes: allNodes.length,
      agents: allNodes.filter((n) => n.group === 'agent' || n.group === 'root').length,
      tools: allNodes.filter((n) => n.group === 'tool').length,
      running: allNodes.filter((n) => n.is_running).length,
      completed: allNodes.filter((n) => !n.is_running).length,
      totalErrors: allNodes.reduce((sum, n) => sum + (n.error_count || 0), 0),
    }
  }

  function updateRunningShadows() {
    if (!nodes || runningNodeIds.size === 0) return
    // Skip animation for large graphs to prevent frame drops
    if (runningNodeIds.size > LARGE_GRAPH_THRESHOLD) return
    animationPhase += 0.15
    const pulsatingSize = getPulsatingShadowSize()
    // Batch update all running nodes at once (instead of per-node update)
    const updates: any[] = []
    runningNodeIds.forEach((nodeId) => {
      const node = nodes!.get(nodeId)
      if (node?.shadow?.size > 15) {
        updates.push({
          id: nodeId,
          shadow: { ...node.shadow, size: pulsatingSize },
        })
      }
    })
    if (updates.length > 0) nodes!.update(updates)
  }

  function animationLoop() {
    updateRunningShadows()
    animationHandle = requestAnimationFrame(animationLoop)
  }

  function startAutoRefresh() {
    stopAutoRefresh()
    // Animation via requestAnimationFrame (smooth, no polling)
    animationHandle = requestAnimationFrame(animationLoop)
    // Data fetching on adaptive interval
    const interval = stats.value.running > 0 ? POLL_ACTIVE_MS : POLL_IDLE_MS
    fetchInterval = setInterval(loadGraphData, interval)
  }

  function adjustPollingInterval() {
    // Re-start fetch interval if running state changed
    if (!fetchInterval) return
    clearInterval(fetchInterval)
    const interval = stats.value.running > 0 ? POLL_ACTIVE_MS : POLL_IDLE_MS
    fetchInterval = setInterval(loadGraphData, interval)
  }

  function stopAutoRefresh() {
    if (animationHandle) {
      cancelAnimationFrame(animationHandle)
      animationHandle = null
    }
    if (fetchInterval) {
      clearInterval(fetchInterval)
      fetchInterval = null
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
    runningNodeIds.clear()
    graphNodeData.clear()
    api.resetGraphSequence()
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
