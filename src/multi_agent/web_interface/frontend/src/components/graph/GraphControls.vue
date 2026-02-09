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
    <Button
      :label="layoutType === 'hierarchical' ? 'Hierarchical' : 'Physics'"
      :icon="layoutType === 'hierarchical' ? 'pi pi-sitemap' : 'pi pi-circle'"
      size="small"
      text
      @click="emit('toggle-layout')"
    />
    <Button label="Fit" icon="pi pi-arrows-alt" size="small" text @click="emit('fit')" />
    <Button label="Reset" icon="pi pi-refresh" size="small" text @click="emit('reset')" />
    <Button
      :label="physicsEnabled ? 'Disable Physics' : 'Enable Physics'"
      size="small"
      text
      @click="emit('toggle-physics')"
    />
    <span class="controls-separator" />
    <Button label="Export" icon="pi pi-image" size="small" text @click="emit('export')" />
    <Button label="Stop" icon="pi pi-stop" size="small" severity="danger" text @click="emit('stop')" />
  </div>
</template>

<style scoped>
.graph-controls {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.controls-separator {
  width: 1px;
  height: 20px;
  background: var(--p-surface-300);
  margin: 0 0.25rem;
}
</style>
