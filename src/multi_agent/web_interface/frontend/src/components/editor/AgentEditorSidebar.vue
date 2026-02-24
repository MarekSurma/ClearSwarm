<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import type { AgentInfo } from '@/types/agent'

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
  if (agentNames.value.has(cloneName.value.trim())) return 'Name already exists'
  if (!/^[a-zA-Z0-9_-]+$/.test(cloneName.value.trim())) return 'Only letters, numbers, _ and -'
  return null
})

function startClone(agentName: string, event: Event) {
  event.stopPropagation()
  cloningAgent.value = agentName
  cloneName.value = agentName + '_copy'
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
  emit('clone', agentName, cloneName.value.trim())
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
          @click="emit('select', agent.name)"
        >
          <div class="item-content">
            <div class="item-name">{{ agent.name }}</div>
            <div class="item-desc">{{ agent.description }}</div>
          </div>
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
  max-height: 70vh;
  overflow-y: auto;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.625rem 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.agent-item:hover {
  background: var(--p-surface-100);
}

.agent-item.active {
  background: var(--p-primary-50);
  border-left: 3px solid var(--p-primary-color);
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 0.125rem;
}

.item-desc {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  line-height: 1.3;
}

.item-actions {
  display: flex;
  flex-shrink: 0;
  gap: 0;
  opacity: 0;
  transition: opacity 0.15s ease;
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
