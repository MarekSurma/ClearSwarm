<script setup lang="ts">
import { ref, computed } from 'vue'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { useToast } from 'primevue/usetoast'
import type { AgentExecution } from '@/types/execution'
import { toDisplayName } from '@/utils/nameFormatting'

const props = defineProps<{
  execution: AgentExecution
}>()

const emit = defineEmits<{
  viewGraph: [agentId: string]
}>()

const toast = useToast()
const showQuestionModal = ref(false)
const showAnswerModal = ref(false)

function copyToClipboard(text: string) {
  if (!text) return

  const handleSuccess = () => {
    toast.add({
      severity: 'success',
      summary: 'Copied',
      detail: 'Content copied to clipboard',
      life: 2000
    })
  }

  // Modern clipboard API
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(handleSuccess).catch(err => {
      console.error('Failed to copy using clipboard API:', err)
      fallbackCopy(text, handleSuccess)
    })
  } else {
    fallbackCopy(text, handleSuccess)
  }
}

function fallbackCopy(text: string, onSuccess: () => void) {
  const textArea = document.createElement('textarea')
  textArea.value = text
  
  // Ensure textarea is not visible but part of the document
  textArea.style.position = 'fixed'
  textArea.style.left = '-9999px'
  textArea.style.top = '0'
  document.body.appendChild(textArea)
  
  textArea.focus()
  textArea.select()
  
  try {
    const successful = document.execCommand('copy')
    if (successful) onSuccess()
  } catch (err) {
    console.error('Fallback copy failed:', err)
  }
  
  document.body.removeChild(textArea)
}

function calculateDuration(start: string, end: string | null): string {
  if (!end) return 'Running...'
  const diffMs = new Date(end).getTime() - new Date(start).getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour > 0) return `${diffHour}h ${diffMin % 60}m`
  if (diffMin > 0) return `${diffMin}m ${diffSec % 60}s`
  return `${diffSec}s`
}

const startedAt = computed(() => new Date(props.execution.started_at).toLocaleString())
const duration = computed(() => calculateDuration(props.execution.started_at, props.execution.completed_at))
const shortId = computed(() => props.execution.agent_id.substring(0, 8))
const statusSeverity = computed(() => (props.execution.is_running ? 'warn' : 'success'))
const statusLabel = computed(() => (props.execution.is_running ? 'Running' : 'Completed'))

const truncatedQuestion = computed(() => {
  const q = props.execution.question || ''
  return q.length > 200 ? q.substring(0, 200) + '...' : q
})

const truncatedAnswer = computed(() => {
  const a = props.execution.final_response || ''
  return a.length > 200 ? a.substring(0, 200) + '...' : a
})
</script>

<template>
  <div class="execution-card" :class="{ running: execution.is_running }">
    <div class="card-header">
      <div class="card-title">
        <span class="agent-name">{{ toDisplayName(execution.agent_name) }}</span>
        <span v-if="execution.parent_agent_id" class="parent-label">
          &larr; {{ toDisplayName(execution.parent_agent_name) }}
        </span>
      </div>
      <Tag :value="statusLabel" :severity="statusSeverity" />
    </div>

    <div class="card-meta">
      <span>{{ startedAt }}</span>
      <span>{{ duration }}</span>
      <span class="mono">{{ shortId }}</span>
    </div>

    <div class="card-actions">
      <Button
        label="Graph"
        icon="pi pi-sitemap"
        size="small"
        text
        @click="emit('viewGraph', execution.agent_id)"
      />
      <div class="qa-badges" v-if="execution.question || execution.final_response">
        <Tag
          v-if="execution.question"
          severity="info"
          class="clickable-tag"
          v-tooltip.bottom="truncatedQuestion"
          @click="showQuestionModal = true"
        >
          <template #default>
            <i class="pi pi-question-circle" style="font-size: 0.8rem; margin-right: 0.25rem"></i>
            Question
          </template>
        </Tag>
        <Tag
          v-if="execution.final_response"
          severity="secondary"
          class="clickable-tag"
          v-tooltip.bottom="truncatedAnswer"
          @click="showAnswerModal = true"
        >
          <template #default>
            <i class="pi pi-check-circle" style="font-size: 0.8rem; margin-right: 0.25rem"></i>
            Answer
          </template>
        </Tag>
      </div>
    </div>

    <!-- Modals -->
    <Dialog v-model:visible="showQuestionModal" header="Question" modal :style="{ width: '60vw' }">
      <div class="modal-content-wrapper">
        <Button
          icon="pi pi-copy"
          class="copy-btn-overlay"
          v-tooltip.left="'Copy to clipboard'"
          text
          rounded
          @click="copyToClipboard(execution.question || '')"
        />
        <pre class="full-text">{{ execution.question }}</pre>
      </div>
    </Dialog>

    <Dialog v-model:visible="showAnswerModal" header="Answer" modal :style="{ width: '60vw' }">
      <div class="modal-content-wrapper">
        <Button
          icon="pi pi-copy"
          class="copy-btn-overlay"
          v-tooltip.left="'Copy to clipboard'"
          text
          rounded
          @click="copyToClipboard(execution.final_response || '')"
        />
        <pre class="full-text">{{ execution.final_response }}</pre>
      </div>
    </Dialog>
  </div>
</template>

<style scoped>
.execution-card {
  padding: 0.75rem 0.875rem;
  border: 1px solid var(--p-surface-200);
  border-radius: 8px;
  transition: border-color 0.15s ease;
  background: var(--p-surface-0);
}

.execution-card.running {
  border-left: 3px solid var(--p-yellow-500);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
}

.card-title {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  overflow: hidden;
}

.agent-name {
  font-weight: 600;
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.parent-label {
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  white-space: nowrap;
}

.card-meta {
  display: flex;
  gap: 0.75rem;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  margin-bottom: 0.5rem;
}

.mono {
  font-family: 'Courier New', monospace;
}

.card-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  border-top: 1px solid var(--p-surface-100);
  padding-top: 0.5rem;
}

.qa-badges {
  display: flex;
  gap: 0.4rem;
}

.clickable-tag {
  cursor: pointer;
  padding: 0.1rem 0.5rem;
  font-size: 0.75rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
}

.modal-content-wrapper {
  position: relative;
}

.copy-btn-overlay {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  z-index: 10;
  background: rgba(255, 255, 255, 0.7) !important;
  backdrop-filter: blur(2px);
}

.full-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  background: var(--p-surface-50);
  padding: 1rem;
  padding-right: 3rem;
  border-radius: 4px;
  font-family: inherit;
  margin: 0;
  max-height: 60vh;
  overflow-y: auto;
}
</style>
