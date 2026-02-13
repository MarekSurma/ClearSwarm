<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import Button from 'primevue/button'
import { useVisualGraph } from '@/composables/useVisualGraph'

const emit = defineEmits<{
  nodeClick: [nodeId: string]
}>()

defineExpose({
  buildGraph,
  fitView,
})

const graph = useVisualGraph()
const graphContainer = ref<HTMLDivElement | null>(null)

onMounted(() => {
  if (graphContainer.value) {
    graph.initialize(graphContainer.value, handleNodeClick)
  }
})

onUnmounted(() => {
  graph.cleanup()
})

function handleNodeClick(nodeId: string) {
  emit('nodeClick', nodeId)
}

function buildGraph(rootAgentName: string, allAgents: string[]) {
  graph.buildGraphForAgent(rootAgentName, allAgents)
}

function fitView() {
  graph.fitView()
}
</script>

<template>
  <div class="visual-graph-canvas">
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

    <!-- Graph container -->
    <div ref="graphContainer" class="graph-container" />

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
  background: #0a0a0a;
}

.graph-toolbar {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem;
  border-bottom: 1px solid var(--p-surface-200);
  background: var(--p-surface-50);
}

.graph-container {
  flex: 1;
  min-height: 400px;
  background: #0a0a0a;
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
