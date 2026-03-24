<script setup lang="ts">
import { ref, computed } from 'vue'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Badge from 'primevue/badge'
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
    <div class="monitor-actions">
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
        <Tab value="roots">
          <div class="tab-label">
            <i class="pi pi-list"></i>
            <span>All</span>
            <Badge :value="rootExecutions.length" severity="secondary" size="small"></Badge>
          </div>
        </Tab>
        <Tab value="running">
          <div class="tab-label">
            <i class="pi pi-play" :class="{ 'pi-spin': runningExecutions.length > 0 }"></i>
            <span>Running</span>
            <Badge
              :value="runningExecutions.length"
              :severity="runningExecutions.length > 0 ? 'success' : 'secondary'"
              size="small"
            ></Badge>
          </div>
        </Tab>
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
              <Message v-if="hiddenRootCount > 0" severity="secondary" :closable="false">
                + {{ hiddenRootCount }} more ({{ rootExecutions.length }} total)
              </Message>
            </template>
            <Message v-else severity="secondary" :closable="false" icon="pi pi-inbox">
              No executions found
            </Message>
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
              <Message v-if="hiddenRunningCount > 0" severity="secondary" :closable="false">
                + {{ hiddenRunningCount }} more ({{ runningExecutions.length }} total)
              </Message>
            </template>
            <Message v-else severity="secondary" :closable="false" icon="pi pi-inbox">
              No running agents
            </Message>
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

.monitor-actions {
  display: flex;
  justify-content: flex-end;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.execution-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 70vh;
  overflow-y: auto;
  padding-top: 0.5rem;
}
</style>
