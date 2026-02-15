<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import { useApi } from '@/composables/useApi'
import { useToast } from 'primevue/usetoast'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  saved: [agentName: string]
}>()

const api = useApi()
const toast = useToast()

const name = ref('')
const description = ref('')
const systemPrompt = ref('')
const isSaving = ref(false)

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      // Reset form when modal opens
      name.value = ''
      description.value = ''
      systemPrompt.value = ''
    }
  }
)

async function save() {
  // Validation
  if (!name.value.trim()) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Agent name is required',
      life: 3000,
    })
    return
  }

  if (!description.value.trim()) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Description is required',
      life: 3000,
    })
    return
  }

  isSaving.value = true

  try {
    await api.createAgent({
      name: name.value.trim(),
      description: description.value.trim(),
      system_prompt: systemPrompt.value,
      tools: [], // New agents start with no tools
    })

    toast.add({
      severity: 'success',
      summary: 'Agent Created',
      detail: `Agent "${name.value}" created successfully`,
      life: 3000,
    })

    emit('saved', name.value.trim())
    emit('update:visible', false)
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'Failed to create agent',
      life: 5000,
    })
  } finally {
    isSaving.value = false
  }
}

function cancel() {
  emit('update:visible', false)
}
</script>

<template>
  <Dialog
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    header="New Agent"
    modal
    :style="{ width: '600px' }"
  >
    <div class="modal-content">
      <div class="field">
        <label for="new-agent-name">Agent Name</label>
        <InputText
          id="new-agent-name"
          v-model="name"
          placeholder="e.g. my_assistant"
          class="w-full"
          autofocus
        />
        <small class="hint">Only letters, numbers, underscores and hyphens allowed</small>
      </div>

      <div class="field">
        <label for="new-agent-description">Description</label>
        <Textarea
          id="new-agent-description"
          v-model="description"
          rows="2"
          class="w-full"
          placeholder="Brief description of what this agent does..."
        />
      </div>

      <div class="field">
        <label for="new-agent-system-prompt">System Prompt</label>
        <Textarea
          id="new-agent-system-prompt"
          v-model="systemPrompt"
          rows="12"
          class="w-full mono-textarea"
          placeholder="Enter the system prompt that defines the agent's behavior..."
        />
      </div>
    </div>

    <template #footer>
      <Button label="Cancel" severity="secondary" :disabled="isSaving" @click="cancel" />
      <Button label="Create Agent" severity="primary" :loading="isSaving" @click="save" />
    </template>
  </Dialog>
</template>

<style scoped>
.modal-content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 0.5rem 0;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
  font-size: 0.9rem;
  color: var(--p-text-color);
}

.hint {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  margin-top: -0.25rem;
}

.mono-textarea :deep(textarea) {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.85rem;
}
</style>
