<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ToolInfo } from '@/types/agent'
import { toDisplayName } from '@/utils/nameFormatting'
import { GRAPH_COLORS } from '@/config/graphColors'

const props = defineProps<{
  tools: ToolInfo[]
}>()

const collapsed = ref(false)

const groupedTools = computed(() => {
  const filtered = props.tools.filter(t => t.name !== 'end_session')
  const groups = new Map<string, ToolInfo[]>()
  for (const tool of filtered) {
    const group = tool.group || tool.name
    if (!groups.has(group)) groups.set(group, [])
    groups.get(group)!.push(tool)
  }
  return Array.from(groups.entries())
})
</script>

<template>
  <div class="tools-sidebar" :class="{ 'is-collapsed': collapsed }">
    <div class="sidebar-header" @click="collapsed = !collapsed">
      <h3 v-tooltip.bottom="'Drag tools onto agent nodes in the graph to assign them.'">Tools</h3>
      <i class="pi collapse-icon" :class="collapsed ? 'pi-chevron-down' : 'pi-chevron-up'" />
    </div>
    <div v-show="!collapsed" class="tool-list">
      <div v-for="[group, groupTools] in groupedTools" :key="group" class="tool-group">
        <div class="group-label">{{ toDisplayName(group) }}</div>
        <div
          v-for="tool in groupTools"
          :key="tool.name"
          class="tool-item"
          draggable="true"
          @dragstart="(e: DragEvent) => { e.dataTransfer?.setData('application/tool-name', tool.name); e.dataTransfer!.effectAllowed = 'copy' }"
          v-tooltip.left="{ value: `<b>${toDisplayName(tool.name)}</b>${tool.description ? '<br><br>' + tool.description : ''}`, escape: false }"
        >
          <div class="item-name">{{ toDisplayName(tool.name) }}</div>
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
  min-height: 0;
  flex: 1;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
  transition: padding 0.15s ease, margin 0.15s ease;
}

.tools-sidebar:not(.is-collapsed) .sidebar-header {
  padding-bottom: 0.75rem;
  margin-bottom: 0.25rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.sidebar-header h3 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.collapse-icon {
  font-size: 0.8rem;
  color: var(--p-text-color);
  opacity: 0.7;
}

.tool-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-top: 0.5rem;
}

.tool-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.group-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--p-text-color);
  padding: 0.15rem 0.5rem;
  letter-spacing: 0.03em;
  text-align: center;
}

.tool-item {
  display: flex;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  cursor: grab;
  background: v-bind('GRAPH_COLORS.tool.background');
  border: none;
  color: v-bind('GRAPH_COLORS.tool.font');
  transition: background 0.15s ease;
}

.tool-item:hover {
  background: v-bind('GRAPH_COLORS.tool.highlightBackground');
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
