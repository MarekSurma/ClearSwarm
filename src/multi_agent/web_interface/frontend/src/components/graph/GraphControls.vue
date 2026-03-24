<script setup lang="ts">
import Button from 'primevue/button'

defineProps<{
  layoutType: string
  physicsEnabled: boolean
}>()

const emit = defineEmits<{
  'toggle-layout': []
  fit: []
  reset: []
  'toggle-physics': []
  export: []
  stop: []
}>()
</script>

<template>
  <div class="graph-controls">
    <div class="control-group">
      <Button
        v-tooltip.bottom="layoutType === 'hierarchical' ? 'Switch to Physics Layout' : 'Switch to Hierarchical Layout'"
        :icon="layoutType === 'hierarchical' ? 'pi pi-sitemap' : 'pi pi-th-large'"
        size="small"
        outlined
        severity="secondary"
        @click="emit('toggle-layout')"
      />
      <Button
        v-tooltip.bottom="physicsEnabled ? 'Disable Physics Simulation' : 'Enable Physics Simulation'"
        :icon="physicsEnabled ? 'pi pi-bolt' : 'pi pi-lock'"
        size="small"
        outlined
        :severity="physicsEnabled ? 'primary' : 'secondary'"
        @click="emit('toggle-physics')"
      />
    </div>

    <div class="control-group">
      <Button v-tooltip.bottom="'Fit View to All Nodes'" icon="pi pi-arrows-alt" size="small" outlined severity="secondary" @click="emit('fit')" />
      <Button v-tooltip.bottom="'Reset Physics & Position'" icon="pi pi-refresh" size="small" outlined severity="secondary" @click="emit('reset')" />
    </div>

    <div class="control-group">
      <Button v-tooltip.bottom="'Export Graph as PNG'" icon="pi pi-image" size="small" outlined severity="secondary" @click="emit('export')" />
      <Button v-tooltip.bottom="'Emergency Stop'" icon="pi pi-stop-circle" size="small" severity="danger" outlined @click="emit('stop')" />
    </div>
  </div>
</template>

<style scoped>
.graph-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  background: var(--p-surface-100);
  padding: 0.25rem;
  border-radius: 6px;
  border: 1px solid var(--p-surface-200);
}

:deep(.p-button.p-button-sm) {
  padding: 0.4rem;
  width: 2rem;
  height: 2rem;
}
</style>
