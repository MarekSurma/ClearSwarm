<script setup lang="ts">
import { ref } from 'vue'
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
const stopping = ref(false)

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

    <Tabs value="roots">
      <TabList>
        <Tab value="roots">Root Executions</Tab>
        <Tab value="all">All Executions</Tab>
        <Tab value="running">Running</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="roots">
          <div class="execution-list">
            <template v-if="rootExecutions.length > 0">
              <ExecutionCard
                v-for="exec in rootExecutions"
                :key="exec.agent_id"
                :execution="exec"
                @view-graph="emit('viewGraph', $event)"
              />
            </template>
            <p v-else class="empty-text">No executions found</p>
          </div>
        </TabPanel>
        <TabPanel value="all">
          <div class="execution-list">
            <template v-if="executions.length > 0">
              <ExecutionCard
                v-for="exec in executions"
                :key="exec.agent_id"
                :execution="exec"
                @view-graph="emit('viewGraph', $event)"
              />
            </template>
            <p v-else class="empty-text">No executions found</p>
          </div>
        </TabPanel>
        <TabPanel value="running">
          <div class="execution-list">
            <template v-if="runningExecutions.length > 0">
              <ExecutionCard
                v-for="exec in runningExecutions"
                :key="exec.agent_id"
                :execution="exec"
                @view-graph="emit('viewGraph', $event)"
              />
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
</style>
