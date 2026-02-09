<script setup lang="ts">
import type { GraphStats } from '@/types/graph'

defineProps<{
  stats: GraphStats
}>()
</script>

<template>
  <div class="graph-stats-bar">
    <div class="stat-item">
      <span class="stat-label">Nodes:</span>
      <span class="stat-value">{{ stats.totalNodes }}</span>
    </div>
    <div class="stat-item">
      <span class="stat-label">Agents:</span>
      <span class="stat-value">{{ stats.agents }}</span>
    </div>
    <div class="stat-item">
      <span class="stat-label">Tools:</span>
      <span class="stat-value">{{ stats.tools }}</span>
    </div>
    <div class="stat-item">
      <span class="stat-label">Running:</span>
      <span class="stat-value running">{{ stats.running }}</span>
    </div>
    <div class="stat-item">
      <span class="stat-label">Completed:</span>
      <span class="stat-value completed">{{ stats.completed }}</span>
    </div>
    <div v-if="stats.totalErrors > 0" class="stat-item">
      <span class="stat-label">Errors:</span>
      <span class="stat-value errors">{{ stats.totalErrors }}</span>
    </div>
  </div>
</template>

<style scoped>
.graph-stats-bar {
  display: flex;
  gap: 1.25rem;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid var(--p-surface-200);
  font-size: 0.8rem;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.stat-label {
  color: var(--p-text-muted-color);
}

.stat-value {
  font-weight: 600;
}

.stat-value.running {
  color: #f59e0b;
}

.stat-value.completed {
  color: #22c55e;
}

.stat-value.errors {
  color: #ef4444;
}
</style>
