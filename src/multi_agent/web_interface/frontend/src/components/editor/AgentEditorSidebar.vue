<script setup lang="ts">
import Button from 'primevue/button'
import type { AgentInfo } from '@/types/agent'

defineProps<{
  agents: AgentInfo[]
  selectedName: string | null
}>()

const emit = defineEmits<{
  select: [name: string]
  new: []
}>()
</script>

<template>
  <div class="editor-sidebar">
    <div class="sidebar-header">
      <h3>Agents</h3>
      <Button icon="pi pi-plus" size="small" rounded @click="emit('new')" />
    </div>
    <div class="agent-list">
      <div
        v-for="agent in agents"
        :key="agent.name"
        class="agent-item"
        :class="{ active: agent.name === selectedName }"
        @click="emit('select', agent.name)"
      >
        <div class="item-name">{{ agent.name }}</div>
        <div class="item-desc">{{ agent.description }}</div>
      </div>
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

.empty-text {
  color: var(--p-text-muted-color);
  text-align: center;
  padding: 1rem;
  font-size: 0.85rem;
}
</style>
