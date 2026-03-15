<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import type { AgentInfo } from '@/types/agent'
import { toDisplayName, toDiskName } from '@/utils/nameFormatting'
import { GRAPH_COLORS } from '@/config/graphColors'

const props = defineProps<{
  agents: AgentInfo[]
  selectedName: string | null
}>()

const emit = defineEmits<{
  select: [name: string]
  new: []
  delete: [name: string]
  clone: [source: string, newName: string]
}>()

const confirmingDelete = ref<string | null>(null)
let confirmTimer: ReturnType<typeof setTimeout> | null = null

function startConfirm(agentName: string, event: Event) {
  event.stopPropagation()
  if (confirmTimer) clearTimeout(confirmTimer)
  confirmingDelete.value = agentName
  confirmTimer = setTimeout(() => {
    confirmingDelete.value = null
  }, 3000)
}

function confirmDelete(agentName: string, event: Event) {
  event.stopPropagation()
  if (confirmTimer) clearTimeout(confirmTimer)
  confirmingDelete.value = null
  emit('delete', agentName)
}

// Clone
const cloningAgent = ref<string | null>(null)
const cloneName = ref('')
const cloneInput = ref<InstanceType<typeof InputText> | null>(null)

const agentNames = computed(() => new Set(props.agents.map((a) => a.name)))

const cloneNameError = computed(() => {
  if (!cloneName.value.trim()) return 'Name is required'
  const diskName = toDiskName(cloneName.value.trim())
  if (agentNames.value.has(diskName)) return 'Name already exists'
  if (!/^[a-zA-Z0-9 _-]+$/.test(cloneName.value.trim())) return 'Only letters, numbers, spaces, _ and -'
  return null
})

function startClone(agentName: string, event: Event) {
  event.stopPropagation()
  cloningAgent.value = agentName
  cloneName.value = toDisplayName(agentName) + ' copy'
  nextTick(() => {
    const el = cloneInput.value?.$el as HTMLInputElement | undefined
    if (el) el.focus()
  })
}

function cancelClone() {
  cloningAgent.value = null
  cloneName.value = ''
}

function submitClone(agentName: string) {
  if (cloneNameError.value) return
  emit('clone', agentName, toDiskName(cloneName.value.trim()))
  cloningAgent.value = null
  cloneName.value = ''
}
</script>

<template>
  <div class="editor-sidebar">
    <div class="sidebar-header">
      <h3>Agents</h3>
      <Button icon="pi pi-plus" size="small" rounded @click="emit('new')" />
    </div>
    <div class="agent-list">
      <template v-for="agent in agents" :key="agent.name">
        <div
          class="agent-item"
          :class="{ active: agent.name === selectedName }"
          draggable="true"
          @dragstart="(e: DragEvent) => { e.dataTransfer?.setData('application/agent-name', agent.name); e.dataTransfer!.effectAllowed = 'copy' }"
          @click="emit('select', agent.name)"
          v-tooltip.right="agent.description || undefined"
        >
          <div class="item-name">{{ toDisplayName(agent.name) }}</div>
          <div class="item-actions">
            <Button
              class="action-btn"
              icon="pi pi-clone"
              size="small"
              severity="secondary"
              text
              rounded
              @click.stop="startClone(agent.name, $event)"
              v-tooltip.top="'Clone agent'"
            />
            <Button
              v-if="confirmingDelete === agent.name"
              class="action-btn confirm-delete"
              icon="pi pi-check"
              size="small"
              severity="danger"
              rounded
              @click="confirmDelete(agent.name, $event)"
              v-tooltip.top="'Confirm delete'"
            />
            <Button
              v-else
              class="action-btn"
              icon="pi pi-trash"
              size="small"
              severity="secondary"
              text
              rounded
              @click="startConfirm(agent.name, $event)"
              v-tooltip.top="'Delete agent'"
            />
          </div>
        </div>
        <div v-if="cloningAgent === agent.name" class="clone-row" @click.stop>
          <InputText
            ref="cloneInput"
            v-model="cloneName"
            size="small"
            class="clone-input"
            :invalid="!!cloneName.trim() && !!cloneNameError"
            placeholder="New agent name"
            @keydown.enter="submitClone(agent.name)"
            @keydown.escape="cancelClone"
          />
          <Button
            icon="pi pi-check"
            size="small"
            severity="success"
            rounded
            :disabled="!!cloneNameError"
            @click="submitClone(agent.name)"
          />
          <Button
            icon="pi pi-times"
            size="small"
            severity="secondary"
            text
            rounded
            @click="cancelClone"
          />
        </div>
      </template>
      <p v-if="agents.length === 0" class="empty-text">No agents found</p>
    </div>
  </div>
</template>

<style scoped>
.editor-sidebar {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-height: 0;
  flex: 1;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.agent-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  cursor: grab;
  background: v-bind('GRAPH_COLORS.agent.background');
  border: 2px solid v-bind('GRAPH_COLORS.agent.border');
  color: v-bind('GRAPH_COLORS.agent.font');
  transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}

.agent-item:active {
  cursor: grabbing;
}

.agent-item:hover {
  background: v-bind('GRAPH_COLORS.agent.highlightBackground');
  border-color: v-bind('GRAPH_COLORS.agent.highlightBorder');
}

.agent-item.active {
  background: v-bind('GRAPH_COLORS.agent.highlightBackground');
  border-color: v-bind('GRAPH_COLORS.agent.highlightBorder');
  box-shadow: 0 0 0 2px v-bind('GRAPH_COLORS.agent.shadow');
}

.item-name {
  flex: 1;
  min-width: 0;
  font-weight: 600;
  font-size: 0.85rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-actions {
  display: flex;
  flex-shrink: 0;
  gap: 0;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.item-actions :deep(.p-button) {
  color: v-bind('GRAPH_COLORS.agent.font');
}

.agent-item:hover .item-actions {
  opacity: 1;
}

.confirm-delete {
  opacity: 1;
}

.item-actions:has(.confirm-delete) {
  opacity: 1;
}

.clone-row {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.75rem;
}

.clone-input {
  flex: 1;
  min-width: 0;
  font-size: 0.8rem;
}

.empty-text {
  color: var(--p-text-muted-color);
  text-align: center;
  padding: 1rem;
  font-size: 0.85rem;
}
</style>
