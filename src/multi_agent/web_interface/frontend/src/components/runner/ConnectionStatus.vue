<script setup lang="ts">
defineProps<{
  connected: boolean
  runningCount: number
}>()
</script>

<template>
  <div class="connection-status">
    <span class="status-dot" :class="connected ? 'online' : 'offline'" />
    <span class="status-text">{{ connected ? 'Connected' : 'Disconnected' }}</span>
    <span class="separator">|</span>
    <span class="running-label">
      Running: <strong>{{ runningCount }}</strong>
    </span>
  </div>
</template>

<style scoped>
.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.online {
  background: var(--p-green-500);
  box-shadow: 0 0 6px color-mix(in srgb, var(--p-green-500), transparent 50%);
}

.status-dot.offline {
  background: var(--p-red-500);
  box-shadow: 0 0 6px color-mix(in srgb, var(--p-red-500), transparent 50%);
}

.separator {
  color: var(--p-surface-400);
}

.running-label strong {
  color: var(--p-text-color);
}
</style>
