<script setup lang="ts">
import type { GraphStats } from '@/types/graph'

defineProps<{
  stats: GraphStats
}>()
</script>

<template>
  <div class="graph-stats-bar">
    <div class="stat-item" v-tooltip.top="'Total active nodes in graph'">
      <i class="pi pi-box stat-icon" />
      <span class="stat-label">Nodes:</span>
      <span class="stat-value">{{ stats.totalNodes }}</span>
    </div>

    <div class="stats-divider" />

    <div class="stat-item" v-tooltip.top="'Number of agent instances'">
      <i class="pi pi-users stat-icon" />
      <span class="stat-label">Agents:</span>
      <span class="stat-value">{{ stats.agents }}</span>
    </div>

    <div class="stat-item" v-tooltip.top="'Number of tool executions'">
      <i class="pi pi-wrench stat-icon" />
      <span class="stat-label">Tools:</span>
      <span class="stat-value">{{ stats.tools }}</span>
    </div>

    <div class="stats-divider" />

    <div class="stat-item" v-tooltip.top="'Tasks currently processing'">
      <i class="pi pi-sync pi-spin stat-icon running" v-if="stats.running > 0" />
      <i class="pi pi-sync stat-icon" v-else />
      <span class="stat-label">Running:</span>
      <span class="stat-value running">{{ stats.running }}</span>
    </div>

    <div class="stat-item" v-tooltip.top="'Tasks completed successfully'">
      <i class="pi pi-check-circle stat-icon completed" />
      <span class="stat-label">Done:</span>
      <span class="stat-value completed">{{ stats.completed }}</span>
    </div>

    <div v-if="stats.totalErrors > 0" class="stat-item" v-tooltip.top="'Tasks that encountered errors'">
      <i class="pi pi-exclamation-circle stat-icon errors" />
      <span class="stat-label">Errors:</span>
      <span class="stat-value errors">{{ stats.totalErrors }}</span>
    </div>
  </div>
</template>

<style scoped>
.graph-stats-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem 1rem;
  background: var(--p-surface-50);
  font-size: 0.8rem;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: background 0.2s;
  cursor: help;
}

.stat-item:hover {
  background: var(--p-surface-100);
}

.stat-icon {
  font-size: 0.9rem;
  color: var(--p-surface-500);
}

.stats-divider {
  width: 1px;
  height: 1.25rem;
  background: var(--p-surface-300);
  margin: 0 0.25rem;
}

.stat-label {
  color: var(--p-text-muted-color);
  font-weight: 500;
}

.stat-value {
  font-weight: 700;
  font-family: 'Courier New', Courier, monospace;
}

.stat-icon.running, .stat-value.running {
  color: var(--p-amber-500);
}

.stat-icon.completed, .stat-value.completed {
  color: var(--p-green-500);
}

.stat-icon.errors, .stat-value.errors {
  color: var(--p-red-500);
}
</style>
