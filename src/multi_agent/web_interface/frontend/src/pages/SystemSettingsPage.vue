<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Toast from 'primevue/toast'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Select from 'primevue/select'
import Message from 'primevue/message'
import { useApi } from '@/composables/useApi'
import type { ModelConnectionInfo } from '@/types/modelConnection'

const NAME_RE = /^[A-Za-z0-9_-]+$/

const api = useApi()
const toast = useToast()

const connections = ref<ModelConnectionInfo[]>([])
const loading = ref(false)

// Create / edit dialog
const showEditDialog = ref(false)
const editMode = ref<'create' | 'edit'>('create')
const editingId = ref<string | null>(null)
const form = ref({ name: '', base_url: '', model: '', api_key: '' })
const hasExistingKey = ref(false)
const saving = ref(false)
const modelOptions = ref<string[]>([])
const fetchingModels = ref(false)

// Clone dialog
const showCloneDialog = ref(false)
const cloneSource = ref<ModelConnectionInfo | null>(null)
const cloneName = ref('')
const cloning = ref(false)

// Delete dialog
const showDeleteDialog = ref(false)
const deleteTarget = ref<ModelConnectionInfo | null>(null)
const deleting = ref(false)

const nameError = computed(() => {
  const n = form.value.name.trim()
  if (!n) return 'Name is required'
  if (!NAME_RE.test(n)) return 'Only letters, digits, hyphens and underscores are allowed'
  return ''
})

const canSave = computed(
  () => !nameError.value && form.value.base_url.trim().length > 0 && !saving.value
)

const cloneNameError = computed(() => {
  const n = cloneName.value.trim()
  if (!n) return 'Name is required'
  if (!NAME_RE.test(n)) return 'Only letters, digits, hyphens and underscores are allowed'
  return ''
})

async function load() {
  loading.value = true
  try {
    connections.value = await api.getModelConnections()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Error', detail: msg(e, 'Failed to load connections'), life: 5000 })
    connections.value = []
  } finally {
    loading.value = false
  }
}

function msg(e: unknown, fallback: string): string {
  return e instanceof Error ? e.message : fallback
}

function openCreate() {
  editMode.value = 'create'
  editingId.value = null
  form.value = { name: '', base_url: '', model: '', api_key: '' }
  hasExistingKey.value = false
  modelOptions.value = []
  showEditDialog.value = true
}

function openEdit(conn: ModelConnectionInfo) {
  editMode.value = 'edit'
  editingId.value = conn.connection_id
  form.value = { name: conn.name, base_url: conn.base_url, model: conn.model, api_key: '' }
  hasExistingKey.value = conn.has_api_key
  modelOptions.value = conn.model ? [conn.model] : []
  showEditDialog.value = true
}

async function fetchModels() {
  if (!form.value.base_url.trim()) {
    toast.add({ severity: 'warn', summary: 'Base URL required', detail: 'Enter a base URL first', life: 3000 })
    return
  }
  fetchingModels.value = true
  try {
    // On edit, let the server use the stored key unless a new one was typed.
    const payload =
      editMode.value === 'edit' && editingId.value && !form.value.api_key
        ? { connection_id: editingId.value, base_url: form.value.base_url }
        : { api_key: form.value.api_key, base_url: form.value.base_url }
    const res = await api.listConnectionModels(payload)
    modelOptions.value = res.models
    if (res.models.length === 0) {
      toast.add({ severity: 'info', summary: 'No models', detail: 'The provider returned no models', life: 3000 })
    } else {
      toast.add({ severity: 'success', summary: 'Models loaded', detail: `${res.models.length} model(s) available`, life: 2500 })
    }
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Could not fetch models', detail: msg(e, 'Connection failed'), life: 5000 })
  } finally {
    fetchingModels.value = false
  }
}

async function saveConnection() {
  if (!canSave.value) return
  saving.value = true
  try {
    if (editMode.value === 'create') {
      await api.createModelConnection({
        name: form.value.name.trim(),
        base_url: form.value.base_url.trim(),
        model: form.value.model || '',
        api_key: form.value.api_key || '',
      })
      toast.add({ severity: 'success', summary: 'Created', detail: `Connection '${form.value.name}' created`, life: 3000 })
    } else if (editingId.value) {
      await api.updateModelConnection(editingId.value, {
        name: form.value.name.trim(),
        base_url: form.value.base_url.trim(),
        model: form.value.model || '',
        // Blank means "keep existing key"
        api_key: form.value.api_key || undefined,
      })
      toast.add({ severity: 'success', summary: 'Saved', detail: `Connection '${form.value.name}' updated`, life: 3000 })
    }
    showEditDialog.value = false
    await load()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Save failed', detail: msg(e, 'Could not save connection'), life: 5000 })
  } finally {
    saving.value = false
  }
}

function openClone(conn: ModelConnectionInfo) {
  cloneSource.value = conn
  cloneName.value = `${conn.name}-copy`
  showCloneDialog.value = true
}

async function confirmClone() {
  if (!cloneSource.value || cloneNameError.value) return
  cloning.value = true
  try {
    await api.cloneModelConnection(cloneSource.value.connection_id, cloneName.value.trim())
    toast.add({ severity: 'success', summary: 'Cloned', detail: `Created '${cloneName.value}'`, life: 3000 })
    showCloneDialog.value = false
    await load()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Clone failed', detail: msg(e, 'Could not clone connection'), life: 5000 })
  } finally {
    cloning.value = false
  }
}

function openDelete(conn: ModelConnectionInfo) {
  deleteTarget.value = conn
  showDeleteDialog.value = true
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.deleteModelConnection(deleteTarget.value.connection_id)
    toast.add({ severity: 'success', summary: 'Deleted', detail: `Connection '${deleteTarget.value.name}' deleted`, life: 3000 })
    showDeleteDialog.value = false
    deleteTarget.value = null
    await load()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Delete failed', detail: msg(e, 'Could not delete connection'), life: 5000 })
  } finally {
    deleting.value = false
  }
}

onMounted(() => load())
</script>

<template>
  <div class="system-settings-page">
    <Toast />

    <div class="page-header">
      <div>
        <h2 class="page-title">System Settings</h2>
        <p class="page-subtitle">Manage AI model connections (OpenAI-compatible providers)</p>
      </div>
      <div class="header-actions">
        <Button label="Add connection" icon="pi pi-plus" severity="primary" @click="openCreate" />
        <Button icon="pi pi-refresh" severity="secondary" text @click="load" v-tooltip.bottom="'Refresh'" />
      </div>
    </div>

    <DataTable
      :value="connections"
      data-key="connection_id"
      :loading="loading"
      striped-rows
      size="small"
      row-hover
    >
      <template #empty>
        <div class="empty-state">
          No model connections yet. Click <strong>Add connection</strong> to create one.
        </div>
      </template>

      <Column field="name" header="Name" sortable>
        <template #body="{ data }">
          <span class="conn-name"><i class="pi pi-server" /> {{ data.name }}</span>
        </template>
      </Column>

      <Column field="base_url" header="Base URL" sortable />

      <Column field="model" header="Model" sortable>
        <template #body="{ data }">
          <span v-if="data.model">{{ data.model }}</span>
          <span v-else class="muted">—</span>
        </template>
      </Column>

      <Column header="API key" header-style="width: 8rem">
        <template #body="{ data }">
          <span v-if="data.has_api_key" class="key-badge set"><i class="pi pi-lock" /> Set</span>
          <span v-else class="key-badge unset"><i class="pi pi-lock-open" /> None</span>
        </template>
      </Column>

      <Column header="" header-style="width: 10rem">
        <template #body="{ data }">
          <div class="row-actions" @click.stop>
            <Button icon="pi pi-pencil" severity="secondary" text rounded size="small" v-tooltip.bottom="'Edit'" @click="openEdit(data)" />
            <Button icon="pi pi-clone" severity="secondary" text rounded size="small" v-tooltip.bottom="'Clone'" @click="openClone(data)" />
            <Button icon="pi pi-trash" severity="danger" text rounded size="small" v-tooltip.bottom="'Delete'" @click="openDelete(data)" />
          </div>
        </template>
      </Column>
    </DataTable>

    <!-- Create / Edit dialog -->
    <Dialog
      v-model:visible="showEditDialog"
      :header="editMode === 'create' ? 'New connection' : 'Edit connection'"
      :modal="true"
      :style="{ width: '520px' }"
    >
      <div class="form">
        <div class="field">
          <label for="conn-name">Name</label>
          <InputText id="conn-name" v-model="form.name" :invalid="!!nameError" placeholder="my-provider" autocomplete="off" />
          <small v-if="nameError" class="field-error">{{ nameError }}</small>
        </div>

        <div class="field">
          <label for="conn-url">Base URL</label>
          <InputText id="conn-url" v-model="form.base_url" placeholder="https://api.openai.com/v1" autocomplete="off" />
        </div>

        <div class="field">
          <label for="conn-key">API key</label>
          <Password
            id="conn-key"
            v-model="form.api_key"
            :feedback="false"
            toggle-mask
            :input-props="{ autocomplete: 'new-password' }"
            :placeholder="editMode === 'edit' && hasExistingKey ? 'Leave blank to keep current key' : 'Enter API key'"
          />
          <small class="field-hint">The key is stored encrypted and can never be read back — only replaced.</small>
        </div>

        <div class="field">
          <label for="conn-model">Model</label>
          <div class="model-row">
            <Select
              id="conn-model"
              v-model="form.model"
              :options="modelOptions"
              editable
              placeholder="Select or type a model name"
              class="model-select"
            />
            <Button
              label="Fetch"
              icon="pi pi-download"
              severity="secondary"
              :loading="fetchingModels"
              @click="fetchModels"
              v-tooltip.bottom="'List available models from the provider'"
            />
          </div>
          <small class="field-hint">Fetch requires a working Base URL and API key.</small>
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showEditDialog = false" />
        <Button
          :label="editMode === 'create' ? 'Create' : 'Save'"
          icon="pi pi-check"
          :loading="saving"
          :disabled="!canSave"
          @click="saveConnection"
        />
      </template>
    </Dialog>

    <!-- Clone dialog -->
    <Dialog v-model:visible="showCloneDialog" header="Clone connection" :modal="true" :style="{ width: '450px' }">
      <Message severity="info" :closable="false" class="clone-info">
        The API key from <strong>{{ cloneSource?.name }}</strong> will be preserved in the clone.
      </Message>
      <div class="field">
        <label for="clone-name">New name</label>
        <InputText id="clone-name" v-model="cloneName" :invalid="!!cloneNameError" autocomplete="off" />
        <small v-if="cloneNameError" class="field-error">{{ cloneNameError }}</small>
      </div>
      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showCloneDialog = false" />
        <Button label="Clone" icon="pi pi-clone" :loading="cloning" :disabled="!!cloneNameError || cloning" @click="confirmClone" />
      </template>
    </Dialog>

    <!-- Delete dialog -->
    <Dialog v-model:visible="showDeleteDialog" header="Delete connection" :modal="true" :style="{ width: '450px' }">
      <p>
        Are you sure you want to delete <strong>{{ deleteTarget?.name }}</strong>?
      </p>
      <p class="warning">This action cannot be undone.</p>
      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showDeleteDialog = false" />
        <Button label="Delete" icon="pi pi-trash" severity="danger" :loading="deleting" @click="confirmDelete" />
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
.system-settings-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1.5rem;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 1rem;
  gap: 1rem;
}

.page-title {
  margin: 0;
  font-size: 1.4rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.page-subtitle {
  margin: 0.25rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.conn-name {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
}

.muted {
  color: var(--p-text-muted-color);
}

.key-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}

.key-badge.set {
  color: var(--p-primary-color);
  background: var(--p-primary-50);
}

.key-badge.unset {
  color: var(--p-text-muted-color);
  background: var(--p-surface-100);
}

.row-actions {
  display: flex;
  gap: 0.25rem;
  justify-content: flex-end;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--p-text-muted-color);
}

.form {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
  padding-top: 0.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.field label {
  font-weight: 500;
  font-size: 0.9rem;
  color: var(--p-text-color);
}

.field :deep(.p-password),
.field :deep(.p-password-input),
.model-select {
  width: 100%;
}

.model-row {
  display: flex;
  gap: 0.5rem;
  align-items: stretch;
}

.model-row .model-select {
  flex: 1;
}

.field-error {
  color: var(--p-red-500);
  font-size: 0.8rem;
}

.field-hint {
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
}

.clone-info {
  margin-bottom: 1rem;
}

.warning {
  color: var(--p-red-500);
  font-weight: 500;
  margin: 0;
}
</style>
