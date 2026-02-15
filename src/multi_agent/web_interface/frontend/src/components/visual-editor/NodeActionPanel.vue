<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Select from 'primevue/select'
import type { AgentInfo, ToolInfo, AgentDetail } from '@/types/agent'

const props = defineProps<{
  nodeId: string | null
  agentDetail: AgentDetail | null
  allAgents: AgentInfo[]
  allTools: ToolInfo[]
  parentAgents: string[]
  isRootNode: boolean
}>()

const emit = defineEmits<{
  addTool: [toolName: string]
  addAgent: [agentName: string]
  editTexts: []
  removeFromParent: [parentAgentName: string]
}>()

const selectedTool = ref<ToolInfo | null>(null)
const selectedAgent = ref<AgentInfo | null>(null)

// Watch nodeId changes to reset selections
watch(
  () => props.nodeId,
  () => {
    selectedTool.value = null
    selectedAgent.value = null
  }
)

const nodeType = computed(() => {
  if (!props.nodeId) return null
  if (props.nodeId.startsWith('agent::')) return 'agent'
  if (props.nodeId.startsWith('tool::')) return 'tool'
  return null
})

const nodeName = computed(() => {
  if (!props.nodeId) return ''
  if (props.nodeId.startsWith('agent::')) {
    return props.nodeId.replace('agent::', '')
  }
  if (props.nodeId.startsWith('tool::')) {
    const match = props.nodeId.match(/^tool::(.+?)::from::/)
    return match ? match[1] : ''
  }
  return ''
})

// Available tools (not already assigned to this agent)
const availableTools = computed(() => {
  if (!props.agentDetail) return []
  const assignedTools = new Set(props.agentDetail.tools)
  return props.allTools.filter((tool) => !assignedTools.has(tool.name))
})

// Available agents (not already assigned to this agent)
const availableAgents = computed(() => {
  if (!props.agentDetail) return []
  const assignedAgents = new Set(props.agentDetail.tools)
  return props.allAgents.filter((agent) => !assignedAgents.has(agent.name))
})

function handleAddTool() {
  if (selectedTool.value) {
    emit('addTool', selectedTool.value.name)
    selectedTool.value = null
  }
}

function handleAddAgent() {
  if (selectedAgent.value) {
    emit('addAgent', selectedAgent.value.name)
    selectedAgent.value = null
  }
}

function handleEditTexts() {
  emit('editTexts')
}

function handleRemoveFromParent(parentName: string) {
  emit('removeFromParent', parentName)
}
</script>

<template>
  <div v-if="nodeId" class="node-action-panel">
    <Card>
      <template #title>
        <div class="panel-header">
          <i :class="nodeType === 'agent' ? 'pi pi-sitemap' : 'pi pi-wrench'" />
          <span>{{ nodeName }}</span>
        </div>
      </template>

      <template #content>
        <div class="actions">
          <!-- Agent actions -->
          <template v-if="nodeType === 'agent'">
            <!-- Add Tool -->
            <div class="action-group">
              <label>Add Tool</label>
              <div class="action-row">
                <Select
                  v-model="selectedTool"
                  :options="availableTools"
                  option-label="name"
                  placeholder="Select tool"
                  class="flex-1"
                  :disabled="availableTools.length === 0"
                />
                <Button
                  icon="pi pi-plus"
                  severity="success"
                  size="small"
                  :disabled="!selectedTool"
                  @click="handleAddTool"
                />
              </div>
            </div>

            <!-- Add Sub-Agent -->
            <div class="action-group">
              <label>Add Sub-Agent</label>
              <div class="action-row">
                <Select
                  v-model="selectedAgent"
                  :options="availableAgents"
                  option-label="name"
                  placeholder="Select agent"
                  class="flex-1"
                  :disabled="availableAgents.length === 0"
                />
                <Button
                  icon="pi pi-plus"
                  severity="success"
                  size="small"
                  :disabled="!selectedAgent"
                  @click="handleAddAgent"
                />
              </div>
            </div>

            <!-- Edit Texts -->
            <Button
              label="Edit Texts"
              icon="pi pi-pencil"
              severity="primary"
              class="w-full"
              @click="handleEditTexts"
            />

            <!-- Remove from parent(s) -->
            <template v-if="!isRootNode && parentAgents.length > 0">
              <div class="divider" />
              <div class="action-group">
                <label>Remove from Parent</label>
                <Button
                  v-for="parent in parentAgents"
                  :key="parent"
                  :label="`Remove from ${parent}`"
                  icon="pi pi-trash"
                  severity="danger"
                  size="small"
                  text
                  class="w-full"
                  @click="handleRemoveFromParent(parent)"
                />
              </div>
            </template>
          </template>

          <!-- Tool actions -->
          <template v-if="nodeType === 'tool'">
            <div class="action-group">
              <label>Remove from Parent</label>
              <Button
                v-for="parent in parentAgents"
                :key="parent"
                :label="`Remove from ${parent}`"
                icon="pi pi-trash"
                severity="danger"
                size="small"
                text
                class="w-full"
                @click="handleRemoveFromParent(parent)"
              />
            </div>
          </template>
        </div>
      </template>
    </Card>
  </div>
</template>

<style scoped>
.node-action-panel {
  position: absolute;
  top: 80px;
  right: 20px;
  width: 320px;
  z-index: 100;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.action-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.action-group label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--p-text-muted-color);
}

.action-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.flex-1 {
  flex: 1;
}

.w-full {
  width: 100%;
}

.divider {
  height: 1px;
  background: var(--p-surface-200);
  margin: 0.5rem 0;
}
</style>
