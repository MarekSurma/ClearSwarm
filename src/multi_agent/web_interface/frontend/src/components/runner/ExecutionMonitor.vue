<script setup lang="ts">
import { ref, computed } from 'vue'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import type { AgentExecution } from '@/types/execution'
import { useApi } from '@/composables/useApi'
import ExecutionCard from './ExecutionCard.vue'

const props = defineProps<{
  executions: AgentExecution[]
  rootExecutions: AgentExecution[]
  runningExecutions: AgentExecution[]
}>()

const emit = defineEmits<{
  viewGraph: [agentId: string]
  stopped: []
}>()

const toast = useToast()
const api = useApi()
const MAX_DISPLAY = 100

const activeTab = ref('roots')
const stopping = ref(false)

const displayedRoot = computed(() => props.rootExecutions.slice(0, MAX_DISPLAY))
const hiddenRootCount = computed(() => Math.max(0, props.rootExecutions.length - MAX_DISPLAY))
const displayedRunning = computed(() => props.runningExecutions.slice(0, MAX_DISPLAY))
const hiddenRunningCount = computed(() => Math.max(0, props.runningExecutions.length - MAX_DISPLAY))

async function stopAll() {
  stopping.value = true
  try {
    const result = await api.stopAllAgents()
    toast.add({ severity: 'success', summary: 'Stopped', detail: result.message, life: 5000 })
    emit('stopped')
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.message, life: 5000 })
  } finally {
    stopping.value = false
  }
}
</script>

<template>
  <div class="execution-monitor">
    <div class="monitor-header">
      <h3>Execution Monitor</h3>
      <Button
        label="Stop All"
        icon="pi pi-stop"
        severity="danger"
        size="small"
        :loading="stopping"
        @click="stopAll"
      />
    </div>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="roots">All</Tab>
        <Tab value="running">Running</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="roots">
          <div class="execution-list">
            <template v-if="rootExecutions.length > 0">
              <ExecutionCard
                v-for="exec in displayedRoot"
                :key="'root-' + exec.agent_id"
                :execution="exec"
                @view-graph="emit('viewGraph', $event)"
              />
              <p v-if="hiddenRootCount > 0" class="overflow-text">
                + {{ hiddenRootCount }} more ({{ rootExecutions.length }} total)
              </p>
            </template>
            <p v-else class="empty-text">No executions found</p>
          </div>
        </TabPanel>
        <TabPanel value="running">
          <div class="execution-list">
            <template v-if="runningExecutions.length > 0">
              <ExecutionCard
                v-for="exec in displayedRunning"
                :key="'running-' + exec.agent_id"
                :execution="exec"
                @view-graph="emit('viewGraph', $event)"
              />
              <p v-if="hiddenRunningCount > 0" class="overflow-text">
                + {{ hiddenRunningCount }} more ({{ runningExecutions.length }} total)
              </p>
            </template>
            <p v-else class="empty-text">No running agents</p>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

<style scoped>
.execution-monitor {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.monitor-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.execution-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 70vh;
  overflow-y: auto;
  padding-top: 0.5rem;
}

.empty-text {
  color: var(--p-text-muted-color);
  text-align: center;
  padding: 2rem;
}

.overflow-text {
  color: var(--p-text-muted-color);
  text-align: center;
  padding: 0.75rem;
  font-size: 0.85rem;
}
</style>
