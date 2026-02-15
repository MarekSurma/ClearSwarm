<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import { useApi } from '@/composables/useApi'
import { useToast } from 'primevue/usetoast'
import type { AgentDetail } from '@/types/agent'

const props = defineProps<{
  visible: boolean
  agentDetail: AgentDetail | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  saved: []
}>()

const api = useApi()
const toast = useToast()

const description = ref('')
const systemPrompt = ref('')
const isSaving = ref(false)

watch(
  () => props.visible,
  (visible) => {
    if (visible && props.agentDetail) {
      description.value = props.agentDetail.description
      systemPrompt.value = props.agentDetail.system_prompt
    }
  }
)

async function save() {
  if (!props.agentDetail) return

  isSaving.value = true

  try {
    await api.updateAgent(props.agentDetail.name, {
      description: description.value,
      system_prompt: systemPrompt.value,
      tools: props.agentDetail.tools, // Keep tools unchanged
    })

    toast.add({
      severity: 'success',
      summary: 'Saved',
      detail: `Agent "${props.agentDetail.name}" updated`,
      life: 3000,
    })

    emit('saved')
    emit('update:visible', false)
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'Failed to update agent',
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
    :header="`Edit Agent: ${agentDetail?.name || ''}`"
    modal
    :style="{ width: '600px' }"
  >
    <div class="modal-content">
      <div class="field">
        <label for="agent-name">Name</label>
        <InputText id="agent-name" :model-value="agentDetail?.name || ''" disabled class="w-full" />
      </div>

      <div class="field">
        <label for="agent-description">Description</label>
        <Textarea
          id="agent-description"
          v-model="description"
          rows="3"
          class="w-full"
          placeholder="Agent description"
        />
      </div>

      <div class="field">
        <label for="agent-system-prompt">System Prompt</label>
        <Textarea
          id="agent-system-prompt"
          v-model="systemPrompt"
          rows="10"
          class="w-full"
          placeholder="System prompt"
        />
      </div>
    </div>

    <template #footer>
      <Button label="Cancel" severity="secondary" :disabled="isSaving" @click="cancel" />
      <Button label="Save" severity="primary" :loading="isSaving" @click="save" />
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
</style>
