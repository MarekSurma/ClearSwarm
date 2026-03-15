<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import Button from 'primevue/button'
import { useVisualGraph } from '@/composables/useVisualGraph'
import { GRAPH_COLORS } from '@/config/graphColors'

const emit = defineEmits<{
  nodeClick: [nodeId: string]
  deselect: []
  dropAgent: [agentName: string, targetAgentName: string]
  dropTool: [toolName: string, targetAgentName: string]
  removeNode: [nodeId: string]
}>()

defineExpose({
  buildGraph,
  fitView,
  getParentAgents: (nodeId: string) => graph.getParentAgents(nodeId),
  addToolNode: (parent: string, tool: string) => graph.addToolNode(parent, tool),
  addSubAgentNode: (parent: string, agent: string, all: string[]) => graph.addSubAgentNode(parent, agent, all),
  removeEdgeFromParent: (nodeId: string, parent: string) => graph.removeEdgeFromParent(nodeId, parent),
})

const graph = useVisualGraph()
const graphContainer = ref<HTMLDivElement | null>(null)
const removeBtn = ref<HTMLDivElement | null>(null)
const hoveredNodeId = ref<string | null>(null)
const removeBtnPos = ref({ x: 0, y: 0 })
const removeBtnScale = ref(1)
const showRemoveBtn = ref(false)

const bgColor = GRAPH_COLORS.background

onMounted(() => {
  if (graphContainer.value) {
    graph.initialize(graphContainer.value, handleNodeClick, handleBackgroundClick, handleNodeHover, handleNodeBlur, handleViewChange)
  }
})

function handleViewChange() {
  if (showRemoveBtn.value && hoveredNodeId.value) {
    updateRemoveBtnPosition(hoveredNodeId.value)
  }
}

onUnmounted(() => {
  graph.cleanup()
})

function handleNodeClick(nodeId: string) {
  emit('nodeClick', nodeId)
}

function handleBackgroundClick() {
  emit('deselect')
}

let blurTimeout: ReturnType<typeof setTimeout> | null = null

function handleNodeHover(nodeId: string) {
  if (blurTimeout) { clearTimeout(blurTimeout); blurTimeout = null }
  if (graph.isRootAgent(nodeId)) {
    showRemoveBtn.value = false
    hoveredNodeId.value = null
    return
  }
  hoveredNodeId.value = nodeId
  updateRemoveBtnPosition(nodeId)
  showRemoveBtn.value = true
}

function handleNodeBlur() {
  blurTimeout = setTimeout(() => {
    showRemoveBtn.value = false
    hoveredNodeId.value = null
  }, 200)
}

function keepRemoveBtn() {
  if (blurTimeout) { clearTimeout(blurTimeout); blurTimeout = null }
}

function leaveRemoveBtn() {
  showRemoveBtn.value = false
  hoveredNodeId.value = null
}

function handleRemoveClick() {
  if (!hoveredNodeId.value) return
  const nodeId = hoveredNodeId.value
  showRemoveBtn.value = false
  hoveredNodeId.value = null
  emit('removeNode', nodeId)
}

function updateRemoveBtnPosition(nodeId: string) {
  if (!graphContainer.value) return
  const edgePos = graph.getNodeRightEdgeDomPosition(nodeId)
  if (!edgePos) return
  const scale = Math.min(Math.max(graph.getScale(), 0.3), 2)
  removeBtnPos.value = { x: edgePos.x - 4, y: edgePos.y - 8 }
  removeBtnScale.value = scale
}

function getNodeAtDomPosition(event: DragEvent): string | null {
  if (!graphContainer.value || !graph.networkInstance()) return null
  const rect = graphContainer.value.getBoundingClientRect()
  const domX = event.clientX - rect.left
  const domY = event.clientY - rect.top
  const nodeId = graph.networkInstance()!.getNodeAt({ x: domX, y: domY })
  return nodeId ? String(nodeId) : null
}

function isDragSupported(event: DragEvent): boolean {
  const types = event.dataTransfer?.types ?? []
  return types.includes('application/agent-name') || types.includes('application/tool-name')
}

function handleDragOver(event: DragEvent) {
  if (!isDragSupported(event)) return
  event.preventDefault()
  event.dataTransfer!.dropEffect = 'copy'

  const nodeId = getNodeAtDomPosition(event)
  if (nodeId && nodeId.startsWith('agent::')) {
    graph.highlightNode(nodeId)
  } else {
    graph.clearHighlight()
  }
}

function handleDragLeave() {
  graph.clearHighlight()
}

function handleDrop(event: DragEvent) {
  event.preventDefault()
  graph.clearHighlight()

  const nodeId = getNodeAtDomPosition(event)
  if (!nodeId || !nodeId.startsWith('agent::')) return
  const targetAgentName = nodeId.replace('agent::', '')

  const agentName = event.dataTransfer?.getData('application/agent-name')
  if (agentName && targetAgentName !== agentName) {
    emit('dropAgent', agentName, targetAgentName)
    return
  }

  const toolName = event.dataTransfer?.getData('application/tool-name')
  if (toolName) {
    emit('dropTool', toolName, targetAgentName)
  }
}

function buildGraph(rootAgentName: string, allAgents: string[]) {
  graph.buildGraphForAgent(rootAgentName, allAgents)
}

function fitView() {
  graph.fitView()
}
</script>

<template>
  <div class="visual-graph-canvas" :style="{ background: bgColor }">
    <!-- Toolbar -->
    <div class="graph-toolbar">
      <Button
        icon="pi pi-arrows-alt"
        label="Fit"
        size="small"
        severity="secondary"
        text
        @click="graph.fitView()"
      />
    </div>

    <!-- Graph area (relative wrapper prevents vis-network resize loop) -->
    <div class="graph-area" @dragover="handleDragOver" @dragleave="handleDragLeave" @drop="handleDrop">
      <div ref="graphContainer" class="graph-container" :style="{ background: bgColor }" />

      <!-- Remove button on hover -->
      <div
        v-if="showRemoveBtn"
        ref="removeBtn"
        class="node-remove-btn"
        :style="{ left: removeBtnPos.x + 'px', top: removeBtnPos.y + 'px', transform: `scale(${removeBtnScale})`, transformOrigin: 'center center' }"
        @mouseenter="keepRemoveBtn"
        @mouseleave="leaveRemoveBtn"
        @click.stop="handleRemoveClick"
      >
        <i class="pi pi-minus" />
      </div>
    </div>

    <!-- Loading overlay -->
    <div v-if="graph.isLoading.value" class="loading-overlay">
      <i class="pi pi-spin pi-spinner" style="font-size: 2rem" />
      <span>Building graph...</span>
    </div>
  </div>
</template>

<style scoped>
.visual-graph-canvas {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.graph-toolbar {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem;
  border-bottom: 1px solid var(--p-surface-200);
  background: var(--p-surface-50);
}

.graph-area {
  flex: 1;
  position: relative;
  overflow: hidden;
  min-height: 0;
}

.graph-container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.node-remove-btn {
  position: absolute;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #c03030;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 0.7rem;
  z-index: 5;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
  transition: transform 0.1s ease, background 0.15s ease;
  pointer-events: auto;
}

.node-remove-btn:hover {
  background: #e03030;
  filter: brightness(1.2);
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  color: var(--p-text-color);
  font-size: 1.1rem;
  z-index: 10;
}
</style>
