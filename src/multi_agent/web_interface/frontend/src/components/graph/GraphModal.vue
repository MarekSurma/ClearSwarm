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

watch(
  () => props.visible,
  async (visible) => {
    if (visible && props.agentId) {
      await nextTick()
      if (graphContainer.value) {
        nodeDetails.clearSelection()
        graph.initializeGraph(props.agentId, graphContainer.value, handleNodeClick)
      }
    } else if (!visible) {
      graph.cleanup()
      nodeDetails.clearSelection()
    }
  }
)

function handleNodeClick(nodeId: string) {
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
        <span class="dialog-title">ClearSwarm Visualizer</span>
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
      </div>
    </template>

    <GraphStats :stats="graph.stats.value" />

    <div class="graph-main-panel">
      <div ref="graphContainer" class="graph-container" />
      <NodeDetailsPanel
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
  gap: 1rem;
  width: 100%;
}

.dialog-title {
  font-weight: 600;
  font-size: 1.1rem;
  white-space: nowrap;
}

.graph-main-panel {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.graph-container {
  flex: 7;
  min-height: 400px;
  background: #0a0a0a;
}
</style>
