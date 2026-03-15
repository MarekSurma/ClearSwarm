<script setup lang="ts">
import type { ToolInfo } from '@/types/agent'
import { toDisplayName } from '@/utils/nameFormatting'
import { GRAPH_COLORS } from '@/config/graphColors'

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
        v-tooltip.left="tool.description || undefined"
      >
        <div class="item-name">{{ toDisplayName(tool.name) }}</div>
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
  min-height: 0;
  flex: 1;
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
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.tool-item {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.45rem 1rem;
  border-radius: 100px;
  cursor: grab;
  background: v-bind('GRAPH_COLORS.tool.background');
  border: 2px solid v-bind('GRAPH_COLORS.tool.border');
  color: v-bind('GRAPH_COLORS.tool.font');
  transition: background 0.15s ease, border-color 0.15s ease;
}

.tool-item:hover {
  background: v-bind('GRAPH_COLORS.tool.highlightBackground');
  border-color: v-bind('GRAPH_COLORS.tool.highlightBorder');
}

.tool-item:active {
  cursor: grabbing;
}

.item-name {
  font-weight: 600;
  font-size: 0.8rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-text {
  color: var(--p-text-muted-color);
  text-align: center;
  padding: 1rem;
  font-size: 0.85rem;
}
</style>
