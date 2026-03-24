<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import Toast from 'primevue/toast'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Message from 'primevue/message'
import FloatLabel from 'primevue/floatlabel'
import Fluid from 'primevue/fluid'

import { useSchedules } from '@/composables/useSchedules'
import { useAgents } from '@/composables/useAgents'
import { useApi } from '@/composables/useApi'
import type { ScheduleInfo, CreateScheduleRequest, ScheduleType } from '@/types/schedule'
import { toDisplayName } from '@/utils/nameFormatting'

const { schedules, loadSchedules } = useSchedules()
const { agents, loadAgents } = useAgents()
const api = useApi()
const toast = useToast()

const loading = ref(false)
const showDialog = ref(false)
const showDeleteDialog = ref(false)
const editingSchedule = ref<ScheduleInfo | null>(null)
const scheduleToDelete = ref<ScheduleInfo | null>(null)

const formData = ref<CreateScheduleRequest>({
  name: '',
  agent_name: '',
  message: '',
  schedule_type: 'hours' as ScheduleType,
  interval_value: 1,
  start_from: null,
  enabled: true,
})

const scheduleTypeOptions = [
  { label: 'Minutes', value: 'minutes' },
  { label: 'Hours', value: 'hours' },
  { label: 'Weeks', value: 'weeks' },
]

const agentOptions = computed(() => {
  return agents.value.map(agent => ({
    label: toDisplayName(agent.name),
    value: agent.name,
  }))
})

const isFormValid = computed(() => {
  return formData.value.name && formData.value.agent_name && formData.value.interval_value >= 1
})

function openCreateDialog() {
  editingSchedule.value = null
  formData.value = {
    name: '',
    agent_name: '',
    message: '',
    schedule_type: 'hours',
    interval_value: 1,
    start_from: null,
    enabled: true,
  }
  showDialog.value = true
}

function openEditDialog(schedule: ScheduleInfo) {
  editingSchedule.value = schedule
  formData.value = {
    name: schedule.name,
    agent_name: schedule.agent_name,
    message: schedule.message,
    schedule_type: schedule.schedule_type,
    interval_value: schedule.interval_value,
    start_from: schedule.start_from,
    enabled: schedule.enabled,
  }
  showDialog.value = true
}

async function saveSchedule() {
  try {
    if (editingSchedule.value) {
      await api.updateSchedule(editingSchedule.value.schedule_id, formData.value)
      toast.add({ severity: 'success', summary: 'Success', detail: 'Plan updated', life: 3000 })
    } else {
      await api.createSchedule(formData.value)
      toast.add({ severity: 'success', summary: 'Success', detail: 'Plan created', life: 3000 })
    }
    showDialog.value = false
    await loadSchedules()
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.message, life: 5000 })
  }
}

function confirmDelete(schedule: ScheduleInfo) {
  scheduleToDelete.value = schedule
  showDeleteDialog.value = true
}

async function deleteSchedule() {
  if (!scheduleToDelete.value) return

  try {
    await api.deleteSchedule(scheduleToDelete.value.schedule_id)
    toast.add({ severity: 'success', summary: 'Success', detail: 'Plan deleted', life: 3000 })
    showDeleteDialog.value = false
    await loadSchedules()
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.message, life: 5000 })
  }
}

async function toggleSchedule(schedule: ScheduleInfo) {
  try {
    await api.toggleSchedule(schedule.schedule_id)
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: `Plan ${schedule.enabled ? 'enabled' : 'disabled'}`,
      life: 3000,
    })
    await loadSchedules()
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.message, life: 5000 })
    schedule.enabled = !schedule.enabled
  }
}

function formatFrequency(schedule: ScheduleInfo): string {
  return `Every ${schedule.interval_value} ${schedule.schedule_type}`
}

function formatDateTime(isoString: string): string {
  const date = new Date(isoString)
  return date.toLocaleString()
}

onMounted(async () => {
  loading.value = true
  await Promise.all([loadSchedules(), loadAgents()])
  loading.value = false
})
</script>

<template>
  <div class="action-plan-page">
    <header class="page-header">
      <div>
        <h1>Action Plans</h1>
        <p class="subtitle">Schedule recurring agent tasks</p>
      </div>
      <Button label="New Plan" icon="pi pi-plus" @click="openCreateDialog" />
    </header>

    <!-- Empty State -->
    <Card v-if="schedules.length === 0 && !loading">
      <template #content>
        <div class="empty-state">
          <i class="pi pi-clock" style="font-size: 3rem; opacity: 0.3"></i>
          <p>No action plans yet</p>
          <Button label="Create First Plan" @click="openCreateDialog" />
        </div>
      </template>
    </Card>

    <!-- Schedules Table -->
    <Card v-else>
      <template #content>
        <DataTable
          :value="schedules"
          size="small"
          stripedRows
          :loading="loading"
        >
          <Column field="name" header="Name" sortable>
            <template #body="{ data }">
              <span
                v-tooltip.top="data.name.length > 30 ? data.name : null"
                class="truncate-text"
                style="max-width: 200px"
              >
                {{ data.name }}
              </span>
            </template>
          </Column>

          <Column field="agent_name" header="Agent" sortable>
            <template #body="{ data }">
              <span
                v-tooltip.top="data.agent_name.length > 20 ? data.agent_name : null"
                class="truncate-text"
                style="max-width: 150px"
              >
                {{ toDisplayName(data.agent_name) }}
              </span>
            </template>
          </Column>

          <Column field="message" header="Message" sortable>
            <template #body="{ data }">
              <span
                v-tooltip.top="data.message && data.message.length > 40 ? data.message : null"
                class="truncate-text"
                style="max-width: 300px"
              >
                {{ data.message || '-' }}
              </span>
            </template>
          </Column>

          <Column field="interval_value" header="Frequency" sortable>
            <template #body="{ data }">
              {{ formatFrequency(data) }}
            </template>
          </Column>

          <Column field="next_run_at" header="Next Run" sortable>
            <template #body="{ data }">
              {{ data.next_run_at ? formatDateTime(data.next_run_at) : '-' }}
            </template>
          </Column>

          <Column field="last_run_at" header="Last Run" sortable>
            <template #body="{ data }">
              {{ data.last_run_at ? formatDateTime(data.last_run_at) : '-' }}
            </template>
          </Column>

          <Column field="enabled" header="Status" sortable>
            <template #body="{ data }">
              <Tag
                :value="data.enabled ? 'Enabled' : 'Disabled'"
                :severity="data.enabled ? 'success' : 'secondary'"
              />
            </template>
          </Column>

          <Column header="Actions" style="width: 180px">
            <template #body="{ data }">
              <div style="display: flex; align-items: center; gap: 0.5rem">
                <ToggleSwitch
                  v-model="data.enabled"
                  @change="toggleSchedule(data)"
                />
                <Button
                  icon="pi pi-pencil"
                  severity="secondary"
                  text
                  size="small"
                  @click="openEditDialog(data)"
                />
                <Button
                  icon="pi pi-trash"
                  severity="danger"
                  text
                  size="small"
                  @click="confirmDelete(data)"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>

    <!-- Create/Edit Dialog -->
    <Dialog
      v-model:visible="showDialog"
      :header="editingSchedule ? 'Edit Plan' : 'New Plan'"
      modal
      :style="{ width: '500px' }"
    >
      <Fluid>
        <div class="dialog-fields">
          <FloatLabel variant="on">
            <InputText
              id="plan-name"
              v-model="formData.name"
            />
            <label for="plan-name">Plan Name *</label>
          </FloatLabel>

          <FloatLabel variant="on">
            <Select
              id="agent"
              v-model="formData.agent_name"
              :options="agentOptions"
              option-label="label"
              option-value="value"
            />
            <label for="agent">Agent *</label>
          </FloatLabel>

          <FloatLabel variant="on">
            <Textarea
              id="message"
              v-model="formData.message"
              rows="3"
            />
            <label for="message">Message</label>
          </FloatLabel>

          <div class="field-group">
            <FloatLabel variant="on">
              <InputNumber
                id="interval"
                v-model="formData.interval_value"
                :min="1"
              />
              <label for="interval">Run every *</label>
            </FloatLabel>
            <FloatLabel variant="on">
              <Select
                id="schedule-type"
                v-model="formData.schedule_type"
                :options="scheduleTypeOptions"
                option-label="label"
                option-value="value"
              />
              <label for="schedule-type">Period *</label>
            </FloatLabel>
          </div>

          <FloatLabel variant="on">
            <InputText
              id="start-from"
              v-model="formData.start_from"
              type="datetime-local"
            />
            <label for="start-from">Starting from (optional)</label>
          </FloatLabel>
        </div>
      </Fluid>

      <template #footer>
        <Button label="Cancel" severity="secondary" @click="showDialog = false" />
        <Button
          :label="editingSchedule ? 'Update' : 'Create'"
          @click="saveSchedule"
          :disabled="!isFormValid"
        />
      </template>
    </Dialog>

    <!-- Delete Confirmation Dialog -->
    <Dialog
      v-model:visible="showDeleteDialog"
      header="Delete Plan"
      modal
      :style="{ width: '400px' }"
    >
      <p>Are you sure you want to delete "{{ scheduleToDelete?.name }}"?</p>
      <template #footer>
        <Button label="Cancel" severity="secondary" @click="showDeleteDialog = false" />
        <Button label="Delete" severity="danger" @click="deleteSchedule" />
      </template>
    </Dialog>

    <Toast />
  </div>
</template>

<style scoped>
.action-plan-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-header h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
}

.subtitle {
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
  margin-top: 0.25rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
  text-align: center;
  gap: 1rem;
}

.empty-state p {
  font-size: 1.1rem;
  color: var(--p-text-muted-color);
  margin: 0;
}

.truncate-text {
  display: inline-block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.dialog-fields {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1rem 0;
}

.field-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
</style>
