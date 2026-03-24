<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import { useGraph } from '@/composables/useGraph'
import { useNodeDetails } from '@/composables/useNodeDetails'
import { useApi } from '@/composables/useApi'
import GraphControls from './GraphControls.vue'
import GraphStats from './GraphStats.vue'
import NodeDetailsPanel from './NodeDetailsPanel.vue'
import { GRAPH_COLORS } from '@/config/graphColors'

const bgColor = GRAPH_COLORS.background

const props = defineProps<{
  visible: boolean
  agentId: string | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const toast = useToast()
const api = useApi()
const graph = useGraph()
const nodeDetails = useNodeDetails()
const graphContainer = ref<HTMLDivElement | null>(null)
const showDetails = ref(true)

watch(
  () => props.visible,
  async (visible) => {
    if (visible && props.agentId) {
      await nextTick()
      if (graphContainer.value) {
        nodeDetails.clearSelection()
        await graph.initializeGraph(props.agentId, graphContainer.value, handleNodeClick)
      }
    } else if (!visible) {
      graph.cleanup()
      nodeDetails.clearSelection()
    }
  }
)

function handleNodeClick(nodeId: string) {
  showDetails.value = true // Auto-show details when node is clicked
  const group = graph.getNodeGroup(nodeId)
  if (group === 'tool') {
    const parentId = graph.getParentAgentId(nodeId)
    if (parentId) {
      nodeDetails.loadToolDetails(nodeId, parentId)
    }
  } else {
    nodeDetails.loadAgentDetails(nodeId)
  }
}

async function stopExecutionTree() {
  if (!props.agentId) return
  try {
    const result = await api.stopAgentTree(props.agentId)
    toast.add({ severity: 'success', summary: 'Stopped', detail: result.message, life: 5000 })
    graph.loadGraphData()
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.message, life: 5000 })
  }
}

function close() {
  emit('update:visible', false)
}
</script>

<template>
  <Dialog
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    modal
    maximizable
    :maximized="true"
    header="ClearSwarm Visualizer"
    :style="{ width: '95vw', height: '90vh' }"
    :contentStyle="{ padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }"
  >
    <template #header>
      <div class="graph-dialog-header">
        <div class="header-left">
          <i class="pi pi-share-alt header-icon" />
          <span class="dialog-title">ClearSwarm Visualizer</span>
        </div>
        <div class="header-actions">
           <Button
            v-tooltip.bottom="showDetails ? 'Collapse Inspection Panel' : 'Expand Inspection Panel'"
            :icon="showDetails ? 'pi pi-layout-sidebar-right' : 'pi pi-layout-sidebar-right-off'"
            size="small"
            text
            severity="secondary"
            @click="showDetails = !showDetails"
          />
        </div>
      </div>
    </template>

    <div class="graph-toolbar">
      <GraphControls
        :layoutType="graph.layoutType.value"
        :physicsEnabled="graph.physicsEnabled.value"
        @toggle-layout="graph.toggleLayout()"
        @fit="graph.fitView()"
        @reset="graph.resetPhysics()"
        @toggle-physics="graph.togglePhysics()"
        @export="graph.exportImage()"
        @stop="stopExecutionTree()"
      />
      <GraphStats :stats="graph.stats.value" />
    </div>

    <div class="graph-main-panel">
      <div ref="graphContainer" class="graph-container" :style="{ background: bgColor }">
        <div class="graph-legend">
          <div class="legend-item"><span class="dot agent"></span> Agent</div>
          <div class="legend-item"><span class="dot tool"></span> Tool</div>
          <div class="legend-item"><span class="dot sync"></span> Sync</div>
          <div class="legend-item"><span class="dot async"></span> Async</div>
        </div>
      </div>

      <NodeDetailsPanel
        v-if="showDetails"
        :nodeType="nodeDetails.nodeType.value"
        :agentLog="nodeDetails.agentLog.value"
        :toolDetail="nodeDetails.toolDetail.value"
        :loading="nodeDetails.loading.value"
        :error="nodeDetails.error.value"
        :isRunning="nodeDetails.isRunning.value"
        @clear="nodeDetails.clearSelection()"
      />
    </div>
  </Dialog>
</template>

<style scoped>
.graph-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 2rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.header-icon {
  font-size: 1.25rem;
  color: var(--p-primary-500);
}

.dialog-title {
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--p-surface-800);
}

.graph-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 1rem;
  background: var(--p-surface-0);
  border-bottom: 1px solid var(--p-surface-200);
  gap: 1rem;
  flex-wrap: wrap;
}

.graph-main-panel {
  display: flex;
  flex: 1;
  overflow: hidden;
  background: var(--p-surface-100);
}

.graph-container {
  flex: 1;
  min-height: 400px;
  position: relative;
}

.graph-legend {
  position: absolute;
  bottom: 1.5rem;
  left: 1.5rem;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(4px);
  padding: 0.75rem;
  border-radius: 8px;
  border: 1px solid var(--p-surface-200);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  z-index: 10;
  pointer-events: none;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-surface-700);
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.dot.agent { background: #4bb7df; border: 1px solid #82dbff; }
.dot.tool { background: #2d6d84; border: 1px solid #82dbff; }
.dot.sync { border: 2px solid #82dbff; background: transparent; }
.dot.async { border: 2px dotted #3e5f6e; background: transparent; }

@media (max-width: 1024px) {
  .graph-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
