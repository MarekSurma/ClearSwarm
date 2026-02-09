<script setup lang="ts">
import { ref, computed } from 'vue'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import type { AgentInfo } from '@/types/agent'
import { useApi } from '@/composables/useApi'

const props = defineProps<{
  agents: AgentInfo[]
}>()

const emit = defineEmits<{
  launched: []
}>()

const toast = useToast()
const api = useApi()

const selectedAgent = ref<string | null>(null)
const message = ref('')
const launching = ref(false)

const agentOptions = computed(() =>
  props.agents.map((a) => ({ label: a.name, value: a.name }))
)

const selectedAgentDescription = computed(() => {
  if (!selectedAgent.value) return ''
  const agent = props.agents.find((a) => a.name === selectedAgent.value)
  return agent?.description || ''
})

async function launchAgent() {
  if (!selectedAgent.value || !message.value.trim()) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Please select an agent and enter a message', life: 5000 })
    return
  }

  launching.value = true
  try {
    const result = await api.runAgent({
      agent_name: selectedAgent.value,
      message: message.value,
    })
    toast.add({
      severity: 'success',
      summary: 'Agent Launched',
      detail: `Agent started. ID: ${result.agent_id.substring(0, 8)}...`,
      life: 5000,
    })
    message.value = ''
    emit('launched')
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.message || 'Failed to launch agent', life: 5000 })
  } finally {
    launching.value = false
  }
}
</script>

<template>
  <div class="agent-launcher">
    <h3>Launch Agent</h3>

    <div class="field">
      <label for="agent-select">Agent</label>
      <Select
        id="agent-select"
        v-model="selectedAgent"
        :options="agentOptions"
        optionLabel="label"
        optionValue="value"
        placeholder="Select an agent..."
        class="w-full"
      />
      <small v-if="selectedAgentDescription" class="agent-desc">
        {{ selectedAgentDescription }}
      </small>
    </div>

    <div class="field">
      <label for="message-input">Message</label>
      <Textarea
        id="message-input"
        v-model="message"
        :rows="4"
        placeholder="Enter your message for the agent..."
        class="w-full"
        @keydown.ctrl.enter="launchAgent"
      />
    </div>

    <Button
      label="Launch Agent"
      icon="pi pi-play"
      :loading="launching"
      :disabled="!selectedAgent || !message.trim()"
      @click="launchAgent"
      class="w-full"
    />
  </div>
</template>

<style scoped>
.agent-launcher {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.agent-launcher h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
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

.agent-desc {
  color: var(--p-text-muted-color);
  font-style: italic;
}

.w-full {
  width: 100%;
}
</style>
