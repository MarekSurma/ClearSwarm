<script setup lang="ts">
import type { ToolInfo } from '@/types/agent'
import { toDisplayName } from '@/utils/nameFormatting'

defineProps<{
  tools: ToolInfo[]
}>()
</script>

<template>
  <div class="tools-sidebar">
    <div class="sidebar-header">
      <h3>Tools</h3>
    </div>
    <div class="tool-list">
      <div
        v-for="tool in tools"
        :key="tool.name"
        class="tool-item"
        draggable="true"
        @dragstart="(e: DragEvent) => { e.dataTransfer?.setData('application/tool-name', tool.name); e.dataTransfer!.effectAllowed = 'copy' }"
      >
        <div class="item-content">
          <div class="item-name">{{ toDisplayName(tool.name) }}</div>
          <div class="item-desc">{{ tool.description }}</div>
        </div>
      </div>
      <p v-if="tools.length === 0" class="empty-text">No tools found</p>
    </div>
  </div>
</template>

<style scoped>
.tools-sidebar {
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

.tool-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  max-height: 70vh;
  overflow-y: auto;
}

.tool-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.625rem 0.75rem;
  border-radius: 6px;
  cursor: grab;
  transition: background 0.15s ease;
}

.tool-item:hover {
  background: var(--p-surface-100);
}

.tool-item:active {
  cursor: grabbing;
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

.empty-text {
  color: var(--p-text-muted-color);
  text-align: center;
  padding: 1rem;
  font-size: 0.85rem;
}
</style>
