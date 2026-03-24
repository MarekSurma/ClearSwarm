<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import type { ExecutionLog, ToolExecution } from '@/types/execution'
import { toDisplayName } from '@/utils/nameFormatting'

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
const showQuestionModal = ref(false)
const showAnswerModal = ref(false)

// Scroll to top when the selected node changes
watch(
  () => props.agentLog?.agent_id,
  async (newId, oldId) => {
    if (newId !== oldId) {
      await nextTick()
      if (scrollContainer.value) {
        scrollContainer.value.scrollTop = 0
      }
    }
  }
)

const initialQuestion = computed(() => {
  if (!props.agentLog?.interactions) return ''
  const firstUserMessage = props.agentLog.interactions.find(m => m.role === 'user')
  return firstUserMessage?.content || ''
})

const truncatedQuestion = computed(() => {
  const q = initialQuestion.value
  return q.length > 100 ? q.substring(0, 100) + '...' : q
})

const truncatedAnswer = computed(() => {
  const a = props.agentLog?.final_response || ''
  return a.length > 100 ? a.substring(0, 100) + '...' : a
})

function escapeHtml(text: string): string {
  if (!text) return ''
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

function formatXmlContent(text: string): string {
  if (!text) return ''
  // First escape HTML entities
  const escaped = escapeHtml(text)
  // Then wrap XML tags in spans with faint color
  return escaped.replace(
    /(&lt;\/?[\w-]+(?:\s+[\w-]+(?:=["'][^"']*["'])?)*\s*\/?&gt;)/g,
    '<span class="xml-tag">$1</span>'
  )
}

function getRoleStyle(role: string) {
  const styles: Record<string, { icon: string; color: string; bg: string }> = {
    user: { icon: 'pi-user', color: 'var(--p-blue-500)', bg: 'rgba(59, 130, 246, 0.05)' },
    assistant: { icon: 'pi-android', color: 'var(--p-green-500)', bg: 'rgba(34, 197, 94, 0.05)' },
    system: { icon: 'pi-cog', color: 'var(--p-amber-500)', bg: 'rgba(245, 158, 11, 0.05)' },
    tool: { icon: 'pi-wrench', color: 'var(--p-violet-500)', bg: 'rgba(139, 92, 246, 0.05)' },
  }
  return styles[role] || { icon: 'pi-comment', color: 'var(--p-surface-400)', bg: 'var(--p-surface-50)' }
}
</script>

<template>
  <div class="node-details-panel">
    <div class="panel-header">
      <div class="panel-title-group">
        <i class="pi pi-file-edit title-icon" />
        <span class="panel-title">Inspection Panel</span>
      </div>
      <Button
        v-tooltip.left="'Close Panel'"
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
        <div class="empty-state-icon">
          <i class="pi pi-mouse" />
        </div>
        <div class="empty-state-text">Select a node in the graph</div>
        <div class="empty-state-subtext">Click on any agent or tool to see its live execution logs and data</div>
      </div>

      <!-- Loading -->
      <div v-else-if="loading" class="empty-state">
        <i class="pi pi-spin pi-spinner empty-state-icon" />
        <div class="empty-state-text">Fetching details...</div>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="empty-state error-text">
        <i class="pi pi-exclamation-triangle empty-state-icon" />
        <div class="empty-state-text">{{ error }}</div>
      </div>

      <!-- Agent details -->
      <template v-else-if="nodeType === 'agent' && agentLog">
        <div class="detail-section highlight">
          <div class="detail-header">
            <span class="detail-name">{{ toDisplayName(agentLog.agent_name) }}</span>
            <Tag
              :value="isRunning ? 'RUNNING' : 'COMPLETED'"
              :severity="isRunning ? 'warn' : 'success'"
              style="font-size: 0.7rem; font-weight: 800"
            />
          </div>
          <div class="detail-meta">
            <i class="pi pi-id-card" /> {{ agentLog.agent_id.substring(0, 12) }}... &bull;
            <i class="pi pi-sync" /> {{ agentLog.total_iterations || 0 }} cycles
          </div>
        </div>

        <div v-if="initialQuestion" class="detail-section">
          <div class="section-label">QUESTION</div>
          <div
            class="result-block clickable"
            v-tooltip.bottom="initialQuestion"
            @click="showQuestionModal = true"
            v-html="escapeHtml(truncatedQuestion)"
          />
        </div>

        <div v-if="agentLog.final_response" class="detail-section">
          <div class="section-label">ANSWER</div>
          <div
            class="result-block clickable"
            v-tooltip.bottom="agentLog.final_response"
            @click="showAnswerModal = true"
            v-html="escapeHtml(truncatedAnswer)"
          />
        </div>

        <div class="section-divider">
          <span>RAW LOG</span>
        </div>

        <div class="conversation">
          <div
            v-for="(msg, idx) in agentLog.interactions"
            :key="`${msg.role}-${idx}`"
            class="message"
            :style="{ borderLeftColor: getRoleStyle(msg.role).color, background: getRoleStyle(msg.role).bg }"
          >
            <div class="message-header">
              <span :style="{ color: getRoleStyle(msg.role).color }">
                <i :class="`pi ${getRoleStyle(msg.role).icon}`" />
                {{ msg.role.toUpperCase() }}
              </span>
              <span class="message-index">#{{ idx + 1 }}</span>
            </div>
            <div class="message-content" v-html="msg.role === 'assistant' ? formatXmlContent(msg.content || '') : escapeHtml(msg.content || '')" />
          </div>
        </div>
      </template>

      <!-- Tool details -->
      <template v-else-if="nodeType === 'tool' && toolDetail">
        <div class="detail-section highlight">
          <div class="detail-header">
            <span class="detail-name">Tool: {{ toDisplayName(toolDetail.tool_name) }}</span>
            <Tag
              :value="toolDetail.is_running ? 'EXECUTING' : 'SUCCESS'"
              :severity="toolDetail.is_running ? 'warn' : 'success'"
              style="font-size: 0.7rem; font-weight: 800"
            />
          </div>
          <div class="detail-meta">
            <i class="pi pi-bolt" /> {{ toolDetail.call_mode === 'asynchronous' ? 'Asynchronous' : 'Synchronous' }}
          </div>
        </div>

        <div class="detail-section">
          <div class="section-label">TIMING</div>
          <div class="info-row">
            <span class="info-label">Started:</span>
            <span class="info-value">{{ new Date(toolDetail.started_at).toLocaleTimeString() }}</span>
          </div>
          <div v-if="toolDetail.completed_at" class="info-row">
            <span class="info-label">Finished:</span>
            <span class="info-value">{{ new Date(toolDetail.completed_at).toLocaleTimeString() }}</span>
          </div>
        </div>

        <div class="detail-section">
          <div class="section-label">PARAMETERS</div>
          <pre class="code-block">{{ JSON.stringify(toolDetail.parameters, null, 2) }}</pre>
        </div>

        <div v-if="toolDetail.result" class="detail-section">
          <div class="section-label">RESULT OUTPUT</div>
          <div class="result-block" v-html="escapeHtml(toolDetail.result)" />
        </div>
      </template>

      <!-- Waiting for log -->
      <div v-else-if="nodeType === 'agent'" class="empty-state">
        <i class="pi pi-spin pi-cog empty-state-icon" />
        <div class="empty-state-text">Streaming agent state...</div>
      </div>
    </div>

    <!-- Modals -->
    <Dialog v-model:visible="showQuestionModal" header="Question" modal :style="{ width: '60vw' }">
      <pre class="full-text-modal">{{ initialQuestion }}</pre>
    </Dialog>

    <Dialog v-model:visible="showAnswerModal" header="Answer" modal :style="{ width: '60vw' }">
      <pre class="full-text-modal">{{ agentLog?.final_response }}</pre>
    </Dialog>
  </div>
</template>

<style scoped>
.node-details-panel {
  flex: 3;
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--p-surface-200);
  background: var(--p-surface-0);
  min-width: 320px;
  max-width: 450px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--p-surface-200);
  background: var(--p-surface-50);
}

.panel-title-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.title-icon {
  font-size: 0.9rem;
  color: var(--p-primary-500);
}

.panel-title {
  font-weight: 700;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05rem;
  color: var(--p-surface-700);
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--p-text-muted-color);
  padding: 4rem 1.5rem;
  gap: 0.75rem;
}

.empty-state-icon {
  font-size: 2rem;
  color: var(--p-surface-300);
  margin-bottom: 0.5rem;
}

.empty-state-text {
  font-weight: 600;
  font-size: 1rem;
  color: var(--p-surface-600);
}

.empty-state-subtext {
  font-size: 0.8rem;
  line-height: 1.5;
}

.error-text {
  color: var(--p-red-500);
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.detail-section.highlight {
  background: var(--p-surface-50);
  padding: 0.75rem;
  border-radius: 8px;
  border: 1px solid var(--p-surface-200);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-name {
  font-weight: 700;
  font-size: 1rem;
  color: var(--p-surface-900);
}

.detail-meta {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.detail-meta i {
  font-size: 0.7rem;
}

.section-divider {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 0.5rem 0;
}

.section-divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--p-surface-200);
}

.section-divider span {
  font-size: 0.7rem;
  font-weight: 800;
  color: var(--p-text-muted-color);
  letter-spacing: 0.1rem;
}

.section-label {
  font-size: 0.75rem;
  font-weight: 800;
  color: var(--p-surface-500);
  letter-spacing: 0.05rem;
  margin-bottom: 0.25rem;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
}

.info-label {
  color: var(--p-text-muted-color);
}

.info-value {
  font-weight: 600;
}

.conversation {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.message {
  border: 1px solid var(--p-surface-200);
  border-left-width: 4px;
  border-radius: 6px;
  padding: 0.75rem;
  font-size: 0.85rem;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.05rem;
}

.message-header i {
  margin-right: 0.25rem;
}

.message-index {
  color: var(--p-text-muted-color);
  font-weight: 400;
}

.message-content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
  max-height: 250px;
  overflow-y: auto;
  color: var(--p-surface-800);
}

.code-block {
  background: var(--p-surface-900);
  color: var(--p-surface-0);
  border-radius: 6px;
  padding: 0.75rem;
  font-size: 0.75rem;
  font-family: 'Fira Code', 'Courier New', monospace;
  white-space: pre-wrap;
  overflow-x: auto;
  margin: 0;
  border: 1px solid var(--p-surface-700);
}

.result-block {
  background: var(--p-surface-50);
  border-radius: 6px;
  padding: 0.75rem;
  font-size: 0.85rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 350px;
  overflow-y: auto;
  border: 1px solid var(--p-surface-200);
  color: var(--p-surface-700);
}

.result-block.clickable {
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.result-block.clickable:hover {
  background: var(--p-surface-100);
  border-color: var(--p-primary-300);
}

.full-text-modal {
  white-space: pre-wrap;
  word-wrap: break-word;
  background: var(--p-surface-50);
  padding: 1rem;
  border-radius: 4px;
  font-family: inherit;
  margin: 0;
  max-height: 60vh;
  overflow-y: auto;
  color: var(--p-surface-800);
}

:deep(.xml-tag) {
  color: var(--p-primary-400) !important;
  font-weight: 600;
}
</style>
