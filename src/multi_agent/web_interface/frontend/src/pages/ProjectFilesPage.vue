<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Toast from 'primevue/toast'
import Dialog from 'primevue/dialog'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useApi } from '@/composables/useApi'
import { useProject } from '@/composables/useProject'

const PREVIEW_EXTENSIONS = new Set([
  'md', 'markdown', 'txt', 'log', 'json', 'yaml', 'yml',
  'csv', 'tsv', 'py', 'js', 'ts', 'vue', 'html', 'css',
  'sh', 'ini', 'toml', 'xml',
])

function fileExt(name: string): string {
  const i = name.lastIndexOf('.')
  return i >= 0 ? name.slice(i + 1).toLowerCase() : ''
}

function isPreviewable(entry: { name: string; is_dir: boolean }): boolean {
  if (entry.is_dir) return false
  return PREVIEW_EXTENSIONS.has(fileExt(entry.name))
}

marked.setOptions({ gfm: true, breaks: false })

const api = useApi()
const toast = useToast()
const { currentProject } = useProject()

type FileEntry = { name: string; path: string; is_dir: boolean; size: number }

const currentPath = ref('')
const entries = ref<FileEntry[]>([])
const selected = ref<FileEntry[]>([])
const loading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const showDeleteDialog = ref(false)
const deleteTargets = ref<FileEntry[]>([])

const showPreviewDialog = ref(false)
const previewLoading = ref(false)
const previewEntry = ref<FileEntry | null>(null)
const previewContent = ref('')
const previewTruncated = ref(false)
const previewMode = ref<'markdown' | 'text'>('text')
const renderRaw = ref(false)

const renderedMarkdown = computed(() => {
  if (previewMode.value !== 'markdown' || renderRaw.value) return ''
  const html = marked.parse(previewContent.value || '') as string
  return DOMPurify.sanitize(html)
})

const breadcrumbs = computed(() => {
  const parts = currentPath.value ? currentPath.value.split('/').filter(Boolean) : []
  const crumbs: { label: string; path: string }[] = [{ label: currentProject.value.project_name, path: '' }]
  let acc = ''
  for (const p of parts) {
    acc = acc ? `${acc}/${p}` : p
    crumbs.push({ label: p, path: acc })
  }
  return crumbs
})

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / Math.pow(1024, i)
  return `${value < 10 && i > 0 ? value.toFixed(2) : value < 100 && i > 0 ? value.toFixed(1) : Math.round(value)} ${units[i]}`
}

async function load() {
  loading.value = true
  try {
    const res = await api.listProjectFiles(currentPath.value)
    entries.value = res.entries
    currentPath.value = res.path
    selected.value = []
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Error', detail: e instanceof Error ? e.message : 'Failed to load files', life: 5000 })
    entries.value = []
  } finally {
    loading.value = false
  }
}

function navigateTo(path: string) {
  currentPath.value = path
  load()
}

function onRowClick(event: { data: FileEntry }) {
  if (event.data.is_dir) {
    navigateTo(event.data.path)
  } else if (isPreviewable(event.data)) {
    openPreview(event.data)
  }
}

async function openPreview(entry: FileEntry) {
  previewEntry.value = entry
  showPreviewDialog.value = true
  previewLoading.value = true
  previewContent.value = ''
  previewTruncated.value = false
  const ext = fileExt(entry.name)
  previewMode.value = (ext === 'md' || ext === 'markdown') ? 'markdown' : 'text'
  renderRaw.value = false
  try {
    const res = await api.getProjectFileContent(entry.path)
    previewContent.value = res.content
    previewTruncated.value = res.truncated
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Preview failed', detail: e instanceof Error ? e.message : 'Failed to load file', life: 5000 })
    showPreviewDialog.value = false
  } finally {
    previewLoading.value = false
  }
}

function triggerUpload() {
  fileInput.value?.click()
}

async function onFilesSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const files = input.files
  if (!files || files.length === 0) return

  let success = 0
  let failed = 0
  for (const f of Array.from(files)) {
    try {
      await api.uploadProjectFile(f, currentPath.value)
      success++
    } catch (err) {
      failed++
      toast.add({ severity: 'error', summary: 'Upload failed', detail: `${f.name}: ${err instanceof Error ? err.message : 'error'}`, life: 5000 })
    }
  }
  if (success > 0) {
    toast.add({ severity: 'success', summary: 'Uploaded', detail: `${success} file(s) uploaded${failed ? `, ${failed} failed` : ''}`, life: 3000 })
  }
  input.value = ''
  load()
}

function downloadEntry(entry: FileEntry) {
  if (entry.is_dir) return
  const url = api.downloadProjectFileUrl(entry.path)
  const a = document.createElement('a')
  a.href = url
  a.download = entry.name
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

function openDeleteDialog(targets: FileEntry[]) {
  deleteTargets.value = targets
  showDeleteDialog.value = true
}

async function confirmDelete() {
  const paths = deleteTargets.value.map(e => e.path)
  try {
    const res = await api.deleteProjectFiles(paths)
    if (res.deleted.length > 0) {
      toast.add({ severity: 'success', summary: 'Deleted', detail: `${res.deleted.length} item(s) deleted`, life: 3000 })
    }
    if (res.errors.length > 0) {
      toast.add({ severity: 'warn', summary: 'Some deletes failed', detail: res.errors.map(e => `${e.path}: ${e.error}`).join('; '), life: 5000 })
    }
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Error', detail: e instanceof Error ? e.message : 'Delete failed', life: 5000 })
  } finally {
    showDeleteDialog.value = false
    deleteTargets.value = []
    load()
  }
}

watch(() => currentProject.value.project_dir, () => {
  currentPath.value = ''
  load()
})

onMounted(() => {
  load()
})
</script>

<template>
  <div class="project-files-page">
    <Toast />

    <div class="page-header">
      <h2 class="page-title">Project Files</h2>
      <div class="header-actions">
        <Button label="Upload" icon="pi pi-upload" severity="primary" @click="triggerUpload" />
        <Button
          label="Delete selected"
          icon="pi pi-trash"
          severity="danger"
          :disabled="selected.length === 0"
          @click="openDeleteDialog(selected)"
        />
        <Button icon="pi pi-refresh" severity="secondary" text @click="load" v-tooltip.bottom="'Refresh'" />
      </div>
    </div>

    <input
      ref="fileInput"
      type="file"
      multiple
      style="display: none"
      @change="onFilesSelected"
    />

    <!-- Breadcrumbs -->
    <nav class="breadcrumbs">
      <template v-for="(crumb, idx) in breadcrumbs" :key="crumb.path">
        <button
          class="crumb"
          :class="{ active: idx === breadcrumbs.length - 1 }"
          @click="navigateTo(crumb.path)"
        >
          <i v-if="idx === 0" class="pi pi-home" />
          <span>{{ crumb.label }}</span>
        </button>
        <span v-if="idx < breadcrumbs.length - 1" class="crumb-sep">/</span>
      </template>
    </nav>

    <DataTable
      v-model:selection="selected"
      :value="entries"
      data-key="path"
      :loading="loading"
      class="files-table"
      striped-rows
      size="small"
      @row-click="onRowClick"
      row-hover
    >
      <template #empty>
        <div class="empty-state">This directory is empty.</div>
      </template>

      <Column selection-mode="multiple" header-style="width: 3rem" />

      <Column field="name" header="Name" sortable>
        <template #body="{ data }">
          <span class="file-cell" :class="{ 'is-dir': data.is_dir, 'is-previewable': !data.is_dir && isPreviewable(data) }">
            <i :class="data.is_dir ? 'pi pi-folder' : 'pi pi-file'" />
            <span>{{ data.name }}</span>
          </span>
        </template>
      </Column>

      <Column field="size" header="Size" sortable header-style="width: 8rem">
        <template #body="{ data }">
          <span class="size-cell">{{ data.is_dir ? '—' : formatSize(data.size) }}</span>
        </template>
      </Column>

      <Column header="" header-style="width: 9rem">
        <template #body="{ data }">
          <div class="row-actions" @click.stop>
            <Button
              v-if="!data.is_dir && isPreviewable(data)"
              icon="pi pi-eye"
              severity="secondary"
              text
              rounded
              size="small"
              v-tooltip.bottom="'Preview'"
              @click="openPreview(data)"
            />
            <Button
              v-if="!data.is_dir"
              icon="pi pi-download"
              severity="secondary"
              text
              rounded
              size="small"
              v-tooltip.bottom="'Download'"
              @click="downloadEntry(data)"
            />
            <Button
              icon="pi pi-trash"
              severity="danger"
              text
              rounded
              size="small"
              v-tooltip.bottom="'Delete'"
              @click="openDeleteDialog([data])"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <Dialog
      v-model:visible="showPreviewDialog"
      :header="previewEntry?.name || 'Preview'"
      :modal="true"
      :style="{ width: '80vw', maxWidth: '1100px' }"
      :content-style="{ height: '75vh', padding: 0 }"
      :dismissable-mask="true"
    >
      <div class="preview-toolbar" v-if="previewEntry">
        <div class="preview-info">
          <i :class="previewMode === 'markdown' ? 'pi pi-book' : 'pi pi-file'" />
          <span>{{ previewEntry.path }}</span>
          <span v-if="previewTruncated" class="truncated-badge">truncated</span>
        </div>
        <div class="preview-actions">
          <Button
            v-if="previewMode === 'markdown'"
            :label="renderRaw ? 'Rendered' : 'Raw'"
            :icon="renderRaw ? 'pi pi-eye' : 'pi pi-code'"
            size="small"
            severity="secondary"
            text
            @click="renderRaw = !renderRaw"
          />
          <Button
            icon="pi pi-download"
            size="small"
            severity="secondary"
            text
            v-tooltip.bottom="'Download'"
            @click="previewEntry && downloadEntry(previewEntry)"
          />
        </div>
      </div>
      <div class="preview-body">
        <div v-if="previewLoading" class="preview-loading">
          <i class="pi pi-spin pi-spinner" /> Loading…
        </div>
        <div
          v-else-if="previewMode === 'markdown' && !renderRaw"
          class="markdown-body"
          v-html="renderedMarkdown"
        />
        <pre v-else class="text-body">{{ previewContent }}</pre>
      </div>
    </Dialog>

    <Dialog
      v-model:visible="showDeleteDialog"
      header="Delete files"
      :modal="true"
      :style="{ width: '450px' }"
    >
      <p>
        Are you sure you want to delete
        <strong>{{ deleteTargets.length }}</strong>
        item<span v-if="deleteTargets.length !== 1">s</span>?
      </p>
      <ul class="delete-list">
        <li v-for="t in deleteTargets.slice(0, 10)" :key="t.path">
          <i :class="t.is_dir ? 'pi pi-folder' : 'pi pi-file'" />
          {{ t.path }}
        </li>
        <li v-if="deleteTargets.length > 10">
          ... and {{ deleteTargets.length - 10 }} more
        </li>
      </ul>
      <p class="warning">This action cannot be undone.</p>
      <template #footer>
        <Button label="Cancel" severity="secondary" @click="showDeleteDialog = false" />
        <Button label="Delete" severity="danger" icon="pi pi-trash" @click="confirmDelete" />
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
.project-files-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1.5rem;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.page-title {
  margin: 0;
  font-size: 1.4rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.breadcrumbs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  background: var(--p-surface-50);
  border: 1px solid var(--p-surface-200);
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.crumb {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  color: var(--p-primary-color);
  font-size: inherit;
}

.crumb:hover {
  background: var(--p-surface-100);
}

.crumb.active {
  color: var(--p-text-color);
  cursor: default;
  font-weight: 500;
}

.crumb.active:hover {
  background: transparent;
}

.crumb-sep {
  color: var(--p-text-muted-color);
}

.files-table :deep(.p-datatable-tbody > tr) {
  cursor: default;
}

.file-cell {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.file-cell.is-dir {
  cursor: pointer;
  color: var(--p-primary-color);
  font-weight: 500;
}

.file-cell.is-dir i {
  color: var(--p-primary-color);
}

.file-cell.is-previewable {
  cursor: pointer;
}

.file-cell.is-previewable:hover {
  color: var(--p-primary-color);
  text-decoration: underline;
}

.preview-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid var(--p-surface-200);
  background: var(--p-surface-50);
  font-size: 0.85rem;
}

.preview-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
}

.preview-info span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.truncated-badge {
  background: var(--p-yellow-100, #fef3c7);
  color: var(--p-yellow-700, #b45309);
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  flex-shrink: 0;
}

.preview-actions {
  display: flex;
  gap: 0.25rem;
  flex-shrink: 0;
}

.preview-body {
  height: calc(75vh - 3rem);
  overflow: auto;
  padding: 1.25rem 1.5rem;
  background: var(--p-content-background, var(--p-surface-0));
}

.preview-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 0.5rem;
  color: var(--p-text-muted-color);
}

.text-body {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.85rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: var(--p-text-color);
}

.markdown-body {
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--p-text-color);
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin: 1.4em 0 0.6em;
  font-weight: 600;
  line-height: 1.25;
  color: var(--p-text-color);
}

.markdown-body :deep(h1) { font-size: 1.75em; border-bottom: 1px solid var(--p-surface-200); padding-bottom: 0.3em; }
.markdown-body :deep(h2) { font-size: 1.4em; border-bottom: 1px solid var(--p-surface-200); padding-bottom: 0.3em; }
.markdown-body :deep(h3) { font-size: 1.2em; }
.markdown-body :deep(h4) { font-size: 1.05em; }

.markdown-body :deep(p) { margin: 0 0 1em; }
.markdown-body :deep(ul),
.markdown-body :deep(ol) { margin: 0 0 1em; padding-left: 1.6em; }
.markdown-body :deep(li) { margin: 0.2em 0; }
.markdown-body :deep(li > p) { margin: 0.2em 0; }

.markdown-body :deep(a) {
  color: var(--p-primary-color);
  text-decoration: none;
}
.markdown-body :deep(a:hover) { text-decoration: underline; }

.markdown-body :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.88em;
  padding: 0.15em 0.4em;
  background: var(--p-surface-100);
  border-radius: 4px;
}

.markdown-body :deep(pre) {
  background: var(--p-surface-100);
  border: 1px solid var(--p-surface-200);
  border-radius: 6px;
  padding: 0.85em 1em;
  overflow-x: auto;
  margin: 0 0 1em;
}

.markdown-body :deep(pre code) {
  background: transparent;
  padding: 0;
  font-size: 0.85em;
}

.markdown-body :deep(blockquote) {
  margin: 0 0 1em;
  padding: 0.3em 1em;
  border-left: 4px solid var(--p-surface-300);
  color: var(--p-text-muted-color);
  background: var(--p-surface-50);
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 0 0 1em;
  width: 100%;
  font-size: 0.92em;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--p-surface-200);
  padding: 0.5em 0.75em;
  text-align: left;
}

.markdown-body :deep(th) {
  background: var(--p-surface-50);
  font-weight: 600;
}

.markdown-body :deep(hr) {
  border: 0;
  border-top: 1px solid var(--p-surface-200);
  margin: 1.5em 0;
}

.markdown-body :deep(img) {
  max-width: 100%;
  height: auto;
}

.size-cell {
  font-variant-numeric: tabular-nums;
  color: var(--p-text-muted-color);
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

.delete-list {
  max-height: 240px;
  overflow-y: auto;
  margin: 0.5rem 0 1rem;
  padding-left: 1.25rem;
  font-size: 0.9rem;
}

.delete-list li {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.warning {
  color: var(--p-red-500);
  font-weight: 500;
  margin: 0;
}
</style>
