<script setup lang="ts">
import { ref, watch } from 'vue'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import type { AgentDetail, ToolInfo, AgentInfo } from '@/types/agent'
import { useApi } from '@/composables/useApi'
import ToolSelector from './ToolSelector.vue'

const props = defineProps<{
  agent: AgentDetail | null
  isNew: boolean
  tools: ToolInfo[]
  allAgents: AgentInfo[]
}>()

const emit = defineEmits<{
  saved: [name: string]
  deleted: []
  cancel: []
}>()

const toast = useToast()
const confirm = useConfirm()
const api = useApi()

const name = ref('')
const description = ref('')
const systemPrompt = ref('')
const selectedTools = ref<string[]>([])
const saving = ref(false)

watch(
  () => props.agent,
  (agent) => {
    if (agent) {
      name.value = agent.name
      description.value = agent.description
      systemPrompt.value = agent.system_prompt
      selectedTools.value = [...agent.tools]
    }
  },
  { immediate: true }
)

watch(
  () => props.isNew,
  (isNew) => {
    if (isNew) {
      name.value = ''
      description.value = ''
      systemPrompt.value = ''
      selectedTools.value = []
    }
  }
)

async function handleSave() {
  if (!name.value.trim() || !description.value.trim()) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Name and description are required', life: 5000 })
    return
  }

  saving.value = true
  try {
    if (props.isNew) {
      await api.createAgent({
        name: name.value.trim(),
        description: description.value.trim(),
        system_prompt: systemPrompt.value,
        tools: selectedTools.value,
      })
    } else {
      await api.updateAgent(name.value, {
        description: description.value.trim(),
        system_prompt: systemPrompt.value,
        tools: selectedTools.value,
      })
    }
    toast.add({ severity: 'success', summary: 'Success', detail: `Agent "${name.value}" saved`, life: 5000 })
    emit('saved', name.value)
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.message, life: 5000 })
  } finally {
    saving.value = false
  }
}

function handleDelete() {
  if (!props.agent) return
  confirm.require({
    message: `Are you sure you want to delete agent "${props.agent.name}"? This action cannot be undone.`,
    header: 'Confirm Delete',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await api.deleteAgent(props.agent!.name)
        toast.add({ severity: 'success', summary: 'Deleted', detail: `Agent "${props.agent!.name}" deleted`, life: 5000 })
        emit('deleted')
      } catch (error: any) {
        toast.add({ severity: 'error', summary: 'Error', detail: error.message, life: 5000 })
      }
    },
  })
}
</script>

<template>
  <div class="editor-form">
    <div class="form-header">
      <h3>{{ isNew ? 'New Agent' : `Edit: ${agent?.name}` }}</h3>
      <div class="form-header-actions">
        <Button
          v-if="!isNew && agent"
          label="Delete"
          icon="pi pi-trash"
          severity="danger"
          size="small"
          text
          @click="handleDelete"
        />
      </div>
    </div>

    <form @submit.prevent="handleSave" class="form-fields">
      <div class="field">
        <label for="agent-name">Agent Name</label>
        <InputText
          id="agent-name"
          v-model="name"
          :disabled="!isNew"
          placeholder="e.g. my_assistant"
          class="w-full"
        />
        <small class="hint">Only letters, numbers, underscores and hyphens allowed</small>
      </div>

      <div class="field">
        <label for="agent-desc">Description</label>
        <Textarea
          id="agent-desc"
          v-model="description"
          :rows="2"
          placeholder="Brief description of what this agent does..."
          class="w-full"
        />
      </div>

      <div class="field">
        <label for="agent-prompt">System Prompt</label>
        <Textarea
          id="agent-prompt"
          v-model="systemPrompt"
          :rows="12"
          placeholder="Enter the system prompt that defines the agent's behavior..."
          class="w-full mono-textarea"
        />
      </div>

      <div class="field">
        <label>Available Tools & Agents</label>
        <ToolSelector
          v-model="selectedTools"
          :tools="tools"
          :agents="allAgents"
        />
      </div>

      <div class="form-actions">
        <Button label="Cancel" size="small" text @click="emit('cancel')" />
        <Button
          label="Save Agent"
          icon="pi pi-save"
          size="small"
          :loading="saving"
          type="submit"
        />
      </div>
    </form>
  </div>
</template>

<style scoped>
.editor-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.form-fields {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.field label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--p-text-muted-color);
}

.hint {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.w-full {
  width: 100%;
}

.mono-textarea :deep(textarea) {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.85rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding-top: 0.5rem;
}
</style>
