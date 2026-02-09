<script setup lang="ts">
import type { AgentInfo } from '@/types/agent'

defineProps<{
  agent: AgentInfo
}>()
</script>

<template>
  <div class="agent-card">
    <div class="agent-name">{{ agent.name }}</div>
    <div class="agent-desc">{{ agent.description }}</div>
  </div>
</template>

<style scoped>
.agent-card {
  padding: 0.75rem;
  border: 1px solid var(--p-surface-200);
  border-radius: 8px;
  transition: border-color 0.15s ease;
}

.agent-card:hover {
  border-color: var(--p-primary-color);
}

.agent-name {
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.agent-desc {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  line-height: 1.3;
}
</style>
