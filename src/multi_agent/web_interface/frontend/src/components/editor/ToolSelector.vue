<script setup lang="ts">
import Checkbox from 'primevue/checkbox'
import type { ToolInfo, AgentInfo } from '@/types/agent'

const props = defineProps<{
  tools: ToolInfo[]
  agents: AgentInfo[]
  modelValue: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

function toggleTool(name: string) {
  const current = [...props.modelValue]
  const idx = current.indexOf(name)
  if (idx >= 0) {
    current.splice(idx, 1)
  } else {
    current.push(name)
  }
  emit('update:modelValue', current)
}
</script>

<template>
  <div class="tool-selector">
    <div class="tool-column">
      <h4>Tools</h4>
      <div class="checkbox-list">
        <div v-for="tool in tools" :key="tool.name" class="checkbox-item" :title="tool.description">
          <Checkbox
            :modelValue="modelValue.includes(tool.name)"
            :binary="true"
            @update:modelValue="toggleTool(tool.name)"
            :inputId="`tool-${tool.name}`"
          />
          <label :for="`tool-${tool.name}`" class="checkbox-label">{{ tool.name }}</label>
        </div>
        <p v-if="tools.length === 0" class="empty-text">No tools available</p>
      </div>
    </div>
    <div class="tool-column">
      <h4>Agents (sub-agents)</h4>
      <div class="checkbox-list">
        <div v-for="agent in agents" :key="agent.name" class="checkbox-item" :title="agent.description">
          <Checkbox
            :modelValue="modelValue.includes(agent.name)"
            :binary="true"
            @update:modelValue="toggleTool(agent.name)"
            :inputId="`agent-${agent.name}`"
          />
          <label :for="`agent-${agent.name}`" class="checkbox-label">{{ agent.name }}</label>
        </div>
        <p v-if="agents.length === 0" class="empty-text">No agents available</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tool-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.tool-column h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}

.checkbox-list {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  max-height: 200px;
  overflow-y: auto;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.checkbox-label {
  font-size: 0.85rem;
  cursor: pointer;
}

.empty-text {
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
}
</style>
