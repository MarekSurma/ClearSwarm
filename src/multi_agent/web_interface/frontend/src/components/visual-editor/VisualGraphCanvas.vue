<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import Button from 'primevue/button'
import { useVisualGraph } from '@/composables/useVisualGraph'
import { GRAPH_COLORS } from '@/config/graphColors'

const emit = defineEmits<{
  nodeClick: [nodeId: string]
  deselect: []
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

const bgColor = GRAPH_COLORS.background

onMounted(() => {
  if (graphContainer.value) {
    graph.initialize(graphContainer.value, handleNodeClick, handleBackgroundClick)
  }
})

onUnmounted(() => {
  graph.cleanup()
})

function handleNodeClick(nodeId: string) {
  emit('nodeClick', nodeId)
}

function handleBackgroundClick() {
  emit('deselect')
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
    <div class="graph-area">
      <div ref="graphContainer" class="graph-container" :style="{ background: bgColor }" />
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
