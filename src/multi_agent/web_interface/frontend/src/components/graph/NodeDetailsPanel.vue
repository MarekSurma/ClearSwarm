<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import type { ExecutionLog, ToolExecution, LogMessage } from '@/types/execution'

const props = defineProps<{
  nodeType: 'agent' | 'tool' | null
  agentLog: ExecutionLog | null
  toolDetail: ToolExecution | null
  loading: boolean
  error: string | null
  isRunning: boolean
}>()

const emit = defineEmits<{
  clear: []
}>()

const scrollContainer = ref<HTMLDivElement | null>(null)

watch(
  () => props.agentLog?.interactions?.length,
  async () => {
    await nextTick()
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
    }
  }
)

function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

function formatXmlContent(text: string): string {
  // First escape HTML entities
  const escaped = escapeHtml(text)
  // Then wrap XML tags in spans with faint color
  // Match both opening tags <tag> and closing tags </tag>, including attributes
  return escaped.replace(
    /(&lt;\/?[\w-]+(?:\s+[\w-]+(?:=["'][^"']*["'])?)*\s*\/?&gt;)/g,
    '<span class="xml-tag">$1</span>'
  )
}

function getRoleStyle(role: string) {
  const styles: Record<string, { icon: string; color: string }> = {
    user: { icon: 'pi-user', color: '#3b82f6' },
    assistant: { icon: 'pi-android', color: '#10b981' },
    system: { icon: 'pi-cog', color: '#f59e0b' },
    tool: { icon: 'pi-wrench', color: '#8b5cf6' },
  }
  return styles[role] || { icon: 'pi-comment', color: '#94a3b8' }
}
</script>

<template>
  <div class="node-details-panel">
    <div class="panel-header">
      <span class="panel-title">Node Details</span>
      <Button
        icon="pi pi-times"
        size="small"
        text
        rounded
        @click="emit('clear')"
      />
    </div>

    <div ref="scrollContainer" class="panel-content">
      <!-- Empty state -->
      <div v-if="!nodeType && !loading" class="empty-state">
        Click on any node in the graph to view its execution details
      </div>

      <!-- Loading -->
      <div v-else-if="loading" class="empty-state">
        Loading node details...
      </div>

      <!-- Error -->
      <div v-else-if="error" class="empty-state error-text">
        {{ error }}
      </div>

      <!-- Agent details -->
      <template v-else-if="nodeType === 'agent' && agentLog">
        <div class="detail-section">
          <div class="detail-header">
            <span class="detail-name">{{ agentLog.agent_name }}</span>
            <Tag
              :value="isRunning ? 'Running' : 'Completed'"
              :severity="isRunning ? 'warn' : 'success'"
            />
          </div>
          <div class="detail-meta">
            {{ agentLog.agent_id.substring(0, 12) }}... &bull;
            {{ agentLog.total_iterations || 0 }} iterations
          </div>
        </div>

        <div class="detail-section">
          <div class="section-label">
            Conversation ({{ agentLog.interactions?.length || 0 }} messages)
          </div>
          <div class="conversation">
            <div
              v-for="(msg, idx) in agentLog.interactions"
              :key="idx"
              class="message"
              :class="`role-${msg.role}`"
            >
              <div class="message-header">
                <span :style="{ color: getRoleStyle(msg.role).color }">
                  <i :class="`pi ${getRoleStyle(msg.role).icon}`" />
                  {{ msg.role }}
                </span>
                <span class="message-index">#{{ idx + 1 }}</span>
              </div>
              <div class="message-content" v-html="msg.role === 'assistant' ? formatXmlContent(msg.content || '') : escapeHtml(msg.content || '')" />
            </div>
          </div>
        </div>
      </template>

      <!-- Tool details -->
      <template v-else-if="nodeType === 'tool' && toolDetail">
        <div class="detail-section">
          <div class="detail-header">
            <span class="detail-name">Tool: {{ toolDetail.tool_name }}</span>
            <Tag
              :value="toolDetail.is_running ? 'Running' : 'Completed'"
              :severity="toolDetail.is_running ? 'warn' : 'success'"
            />
          </div>
          <div class="detail-meta">
            ID: {{ toolDetail.tool_execution_id }} &bull;
            {{ toolDetail.call_mode === 'asynchronous' ? 'Async' : 'Sync' }}
          </div>
        </div>

        <div class="detail-section">
          <div class="section-label">Timing</div>
          <div class="detail-meta">
            Started: {{ new Date(toolDetail.started_at).toLocaleString() }}
          </div>
          <div v-if="toolDetail.completed_at" class="detail-meta">
            Completed: {{ new Date(toolDetail.completed_at).toLocaleString() }}
          </div>
        </div>

        <div class="detail-section">
          <div class="section-label">Parameters</div>
          <pre class="code-block">{{ JSON.stringify(toolDetail.parameters, null, 2) }}</pre>
        </div>

        <div v-if="toolDetail.result" class="detail-section">
          <div class="section-label">Result</div>
          <div class="result-block" v-html="escapeHtml(toolDetail.result)" />
        </div>
      </template>

      <!-- Waiting for log -->
      <div v-else-if="nodeType === 'agent'" class="empty-state">
        Please wait...
      </div>
    </div>
  </div>
</template>

<style scoped>
.node-details-panel {
  flex: 3;
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--p-surface-200);
  min-width: 280px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--p-surface-200);
}

.panel-title {
  font-weight: 600;
  font-size: 0.9rem;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
}

.empty-state {
  text-align: center;
  color: var(--p-text-muted-color);
  padding: 2rem 1rem;
  font-size: 0.85rem;
}

.error-text {
  color: var(--p-red-400);
}

.detail-section {
  margin-bottom: 1rem;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
}

.detail-name {
  font-weight: 600;
  font-size: 0.95rem;
}

.detail-meta {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.section-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  margin-bottom: 0.375rem;
}

.conversation {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.message {
  border: 1px solid var(--p-surface-200);
  border-radius: 6px;
  padding: 0.5rem;
  font-size: 0.8rem;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
}

.message-header i {
  margin-right: 0.25rem;
  font-size: 0.7rem;
}

.message-index {
  color: var(--p-text-muted-color);
  font-weight: 400;
}

.message-content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.4;
  max-height: 200px;
  overflow-y: auto;
}

.code-block {
  background: var(--p-surface-100);
  border-radius: 6px;
  padding: 0.5rem;
  font-size: 0.75rem;
  font-family: 'Courier New', monospace;
  white-space: pre-wrap;
  overflow-x: auto;
  margin: 0;
}

.result-block {
  background: var(--p-surface-100);
  border-radius: 6px;
  padding: 0.5rem;
  font-size: 0.8rem;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
}

:deep(.xml-tag) {
  color: var(--p-surface-400) !important;
  opacity: 0.9 !important;
}
</style>
