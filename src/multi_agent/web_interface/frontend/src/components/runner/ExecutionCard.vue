<script setup lang="ts">
import { computed } from 'vue'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import type { AgentExecution } from '@/types/execution'

const props = defineProps<{
  execution: AgentExecution
}>()

const emit = defineEmits<{
  viewGraph: [agentId: string]
}>()

function calculateDuration(start: string, end: string | null): string {
  if (!end) return 'Running...'
  const diffMs = new Date(end).getTime() - new Date(start).getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour > 0) return `${diffHour}h ${diffMin % 60}m`
  if (diffMin > 0) return `${diffMin}m ${diffSec % 60}s`
  return `${diffSec}s`
}

const startedAt = computed(() => new Date(props.execution.started_at).toLocaleString())
const duration = computed(() => calculateDuration(props.execution.started_at, props.execution.completed_at))
const shortId = computed(() => props.execution.agent_id.substring(0, 8))
const statusSeverity = computed(() => (props.execution.is_running ? 'warn' : 'success'))
const statusLabel = computed(() => (props.execution.is_running ? 'Running' : 'Completed'))
</script>

<template>
  <div class="execution-card" :class="{ running: execution.is_running }">
    <div class="card-header">
      <div class="card-title">
        <span class="agent-name">{{ execution.agent_name }}</span>
        <span v-if="execution.parent_agent_id" class="parent-label">
          &larr; {{ execution.parent_agent_name }}
        </span>
      </div>
      <Tag :value="statusLabel" :severity="statusSeverity" />
    </div>

    <div class="card-meta">
      <span>{{ startedAt }}</span>
      <span>{{ duration }}</span>
      <span class="mono">{{ shortId }}...</span>
    </div>

    <div class="card-actions">
      <Button
        label="View Graph"
        icon="pi pi-sitemap"
        size="small"
        text
        @click="emit('viewGraph', execution.agent_id)"
      />
    </div>
  </div>
</template>

<style scoped>
.execution-card {
  padding: 0.875rem;
  border: 1px solid var(--p-surface-200);
  border-radius: 8px;
  transition: border-color 0.15s ease;
}

.execution-card.running {
  border-left: 3px solid var(--p-yellow-500);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.card-title {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}

.agent-name {
  font-weight: 600;
  font-size: 0.95rem;
}

.parent-label {
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
}

.card-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  margin-bottom: 0.5rem;
}

.mono {
  font-family: 'Courier New', monospace;
}

.card-actions {
  display: flex;
  gap: 0.25rem;
}
</style>
