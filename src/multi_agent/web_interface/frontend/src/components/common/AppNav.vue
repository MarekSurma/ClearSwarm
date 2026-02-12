<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useProject } from '@/composables/useProject'
import type { ProjectInfo } from '@/types/project'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Checkbox from 'primevue/checkbox'
import { useToast } from 'primevue/usetoast'

const route = useRoute()
const toast = useToast()
const { currentProject, projects, pendingProject, hasPendingSwitch, loadProjects, selectProject, switchProject, createProject, cloneProject, deleteProject } = useProject()

// Selected project = pending project if exists, otherwise current project
const selectedProject = computed(() => pendingProject.value || currentProject.value)

// Check if selected project is default
const isSelectedDefault = computed(() => selectedProject.value.project_name === 'default')

// Hover state for action buttons
const showActionButtons = ref(false)
let hideTimer: ReturnType<typeof setTimeout> | null = null

// Timer for pending project switch (10 seconds)
let switchTimer: ReturnType<typeof setTimeout> | null = null

function onMouseEnter() {
  showActionButtons.value = true
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
}

function onMouseLeave() {
  hideTimer = setTimeout(() => {
    showActionButtons.value = false
  }, 10000)
}

// Modal states
const showNewModal = ref(false)
const showCloneModal = ref(false)
const showDeleteModal = ref(false)

// Loading states for modal actions
const isCreatingProject = ref(false)
const isCloningProject = ref(false)
const isDeletingProject = ref(false)

// Frozen project references for modals (immutable snapshot at modal open)
const targetProjectForClone = ref<ProjectInfo | null>(null)
const targetProjectForDelete = ref<ProjectInfo | null>(null)

// New project form
const newProjectName = ref('')
const newProjectCreateTools = ref(false)
const newProjectCreatePrompts = ref(false)

// Clone project form
const cloneProjectName = ref('')
const cloneProjectTools = ref(false)
const cloneProjectPrompts = ref(false)

async function handleNewProject() {
  if (!newProjectName.value.trim()) {
    toast.add({ severity: 'warn', summary: 'Warning', detail: 'Project name is required', life: 3000 })
    return
  }

  isCreatingProject.value = true

  try {
    const newProj = await createProject({
      name: newProjectName.value.trim(),
      create_tools: newProjectCreateTools.value,
      create_prompts: newProjectCreatePrompts.value
    })

    toast.add({ severity: 'success', summary: 'Success', detail: `Project "${newProj.project_name}" created`, life: 3000 })

    // Switch to new project
    switchProject(newProj)

    // Reset form
    newProjectName.value = ''
    newProjectCreateTools.value = false
    newProjectCreatePrompts.value = false
    showNewModal.value = false
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Error', detail: error instanceof Error ? error.message : 'Failed to create project', life: 5000 })
  } finally {
    isCreatingProject.value = false
  }
}

async function handleCloneProject() {
  if (!cloneProjectName.value.trim()) {
    toast.add({ severity: 'warn', summary: 'Warning', detail: 'Project name is required', life: 3000 })
    return
  }

  if (!targetProjectForClone.value) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No project selected for cloning', life: 3000 })
    return
  }

  isCloningProject.value = true

  try {
    const newProj = await cloneProject({
      source_project_dir: targetProjectForClone.value.project_dir,
      new_name: cloneProjectName.value.trim(),
      clone_tools: cloneProjectTools.value,
      clone_prompts: cloneProjectPrompts.value
    })

    toast.add({ severity: 'success', summary: 'Success', detail: `Project "${newProj.project_name}" cloned from "${targetProjectForClone.value.project_name}"`, life: 3000 })

    // Switch to new project
    switchProject(newProj)

    // Reset form
    cloneProjectName.value = ''
    cloneProjectTools.value = false
    cloneProjectPrompts.value = false
    showCloneModal.value = false
    targetProjectForClone.value = null
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Error', detail: error instanceof Error ? error.message : 'Failed to clone project', life: 5000 })
  } finally {
    isCloningProject.value = false
  }
}

async function handleDeleteProject() {
  if (!targetProjectForDelete.value) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No project selected for deletion', life: 3000 })
    return
  }

  isDeletingProject.value = true

  try {
    const deletedProjectName = targetProjectForDelete.value.project_name
    await deleteProject(deletedProjectName)

    // If we deleted the pending project, clear it to remove "Go!" button
    if (pendingProject.value?.project_name === deletedProjectName) {
      pendingProject.value = null
    }

    toast.add({ severity: 'success', summary: 'Success', detail: `Project "${deletedProjectName}" deleted`, life: 3000 })
    showDeleteModal.value = false
    targetProjectForDelete.value = null
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Error', detail: error instanceof Error ? error.message : 'Failed to delete project', life: 5000 })
  } finally {
    isDeletingProject.value = false
  }
}

function handleProjectSelect(project: any) {
  selectProject(project)

  // Clear existing timer
  if (switchTimer) {
    clearTimeout(switchTimer)
  }

  // Start 10-second timer to reset selection
  switchTimer = setTimeout(() => {
    // Reset to current project if not switched
    if (pendingProject.value && pendingProject.value.project_dir !== currentProject.value.project_dir) {
      pendingProject.value = null
    }
    switchTimer = null
  }, 10000)
}

function handleGoClick() {
  // Clear the timer
  if (switchTimer) {
    clearTimeout(switchTimer)
    switchTimer = null
  }

  if (pendingProject.value) {
    switchProject(pendingProject.value)
  }
}

onMounted(async () => {
  try {
    await loadProjects()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load projects', life: 5000 })
  }
})

onUnmounted(() => {
  // Clean up timers
  if (hideTimer) {
    clearTimeout(hideTimer)
  }
  if (switchTimer) {
    clearTimeout(switchTimer)
  }
})
</script>

<template>
  <nav class="app-nav" @mouseenter="onMouseEnter" @mouseleave="onMouseLeave">
    <div class="nav-inner">
      <!-- Left section: Logo + Project selector + Action buttons -->
      <div class="nav-left">
        <router-link to="/" class="nav-brand">
          <img src="@/assets/favicon.svg" alt="ClearSwarm" class="nav-logo" />
          <span class="nav-brand-text">ClearSwarm</span>
        </router-link>

        <!-- Project selector -->
        <div class="project-controls">
          <Select
            v-model="pendingProject"
            :options="projects"
            option-label="project_name"
            placeholder="Select Project"
            class="project-select"
            @update:model-value="handleProjectSelect"
          >
            <template #value="slotProps">
              <span v-if="slotProps.value">{{ slotProps.value.project_name }}</span>
              <span v-else>{{ currentProject.project_name }}</span>
            </template>
          </Select>

          <!-- Go button (visible when pending switch) -->
          <Button
            v-if="hasPendingSwitch"
            severity="success"
            size="small"
            class="go-button"
            @click="handleGoClick"
          >
            <span class="pulsing-dot"></span>
            <span>Go!</span>
          </Button>

          <!-- Action buttons (visible on hover) -->
          <Transition name="fade">
            <div v-show="showActionButtons || hasPendingSwitch" class="action-buttons">
              <Button
                label="Clone"
                icon="pi pi-copy"
                severity="secondary"
                size="small"
                text
                @click="() => { targetProjectForClone = selectedProject; showCloneModal = true }"
              />
              <Button
                label="Delete"
                icon="pi pi-trash"
                severity="danger"
                size="small"
                text
                :disabled="isSelectedDefault"
                @click="() => { targetProjectForDelete = selectedProject; showDeleteModal = true }"
              />
              <Button
                label="New"
                icon="pi pi-plus"
                severity="primary"
                size="small"
                text
                @click="showNewModal = true"
              />
            </div>
          </Transition>
        </div>
      </div>

      <!-- Right section: Navigation links -->
      <div class="nav-links">
        <router-link
          to="/"
          class="nav-link"
          :class="{ active: route.name === 'runner' }"
        >
          <i class="pi pi-play" />
          Runner
        </router-link>
        <router-link
          to="/editor"
          class="nav-link"
          :class="{ active: route.name === 'editor' }"
        >
          <i class="pi pi-pencil" />
          Editor
        </router-link>
      </div>
    </div>

    <!-- New Project Modal -->
    <Dialog v-model:visible="showNewModal" header="Create New Project" :modal="true" :style="{ width: '450px' }">
      <div class="modal-content">
        <div class="field">
          <label for="new-project-name">Project Name</label>
          <InputText
            id="new-project-name"
            v-model="newProjectName"
            :maxlength="20"
            placeholder="Enter project name"
            class="w-full"
          />
        </div>
      </div>
      <template #footer>
        <Button label="Cancel" severity="secondary" :disabled="isCreatingProject" @click="showNewModal = false" />
        <Button
          label="Create"
          severity="primary"
          :disabled="!newProjectName.trim()"
          :loading="isCreatingProject"
          @click="handleNewProject"
        />
      </template>
    </Dialog>

    <!-- Clone Project Modal -->
    <Dialog v-model:visible="showCloneModal" :header="`Clone Project: ${targetProjectForClone?.project_name || ''}`" :modal="true" :style="{ width: '450px' }">
      <div class="modal-content">
        <div class="field">
          <label for="clone-project-name">New Project Name</label>
          <InputText
            id="clone-project-name"
            v-model="cloneProjectName"
            :maxlength="20"
            placeholder="Enter project name"
            class="w-full"
          />
        </div>
        <div class="field-checkbox">
          <Checkbox v-model="cloneProjectPrompts" input-id="clone-prompts" :binary="true" />
          <label for="clone-prompts">Clone prompts</label>
        </div>
        <div class="field-checkbox">
          <Checkbox v-model="cloneProjectTools" input-id="clone-tools" :binary="true" />
          <label for="clone-tools">Clone tools</label>
        </div>
        <p class="hint">Note: Agents are always cloned. Checkboxes are optional.</p>
      </div>
      <template #footer>
        <Button
          label="Cancel"
          severity="secondary"
          :disabled="isCloningProject"
          @click="() => { showCloneModal = false; targetProjectForClone = null }"
        />
        <Button
          label="Clone"
          severity="primary"
          :disabled="!cloneProjectName.trim()"
          :loading="isCloningProject"
          @click="handleCloneProject"
        />
      </template>
    </Dialog>

    <!-- Delete Project Modal -->
    <Dialog v-model:visible="showDeleteModal" header="Delete Project" :modal="true" :style="{ width: '450px' }">
      <div class="modal-content">
        <p>Are you sure you want to delete the project <strong>{{ targetProjectForDelete?.project_name || '' }}</strong>?</p>
        <p class="warning">This action cannot be undone.</p>
      </div>
      <template #footer>
        <Button
          label="No"
          severity="secondary"
          :disabled="isDeletingProject"
          @click="() => { showDeleteModal = false; targetProjectForDelete = null }"
        />
        <Button
          label="Yes"
          severity="danger"
          :loading="isDeletingProject"
          @click="handleDeleteProject"
        />
      </template>
    </Dialog>
  </nav>
</template>

<style scoped>
.app-nav {
  border-bottom: 1px solid var(--p-surface-200);
  padding: 0 1.5rem;
}

.nav-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1600px;
  margin: 0 auto;
  height: 56px;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
  color: var(--p-text-color);
  font-weight: 600;
  font-size: 1.1rem;
}

.nav-logo {
  width: 28px;
  height: 28px;
}

.project-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.project-select {
  width: 200px;
}

.go-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.pulsing-dot {
  width: 8px;
  height: 8px;
  background-color: white;
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(0.8);
  }
}

.action-buttons {
  display: flex;
  gap: 0.25rem;
}

.nav-links {
  display: flex;
  gap: 0.25rem;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  text-decoration: none;
  color: var(--p-text-muted-color);
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.15s ease;
}

.nav-link:hover {
  color: var(--p-text-color);
  background: var(--p-surface-100);
}

.nav-link.active {
  color: var(--p-primary-color);
  background: var(--p-primary-50);
}

/* Modal styles */
.modal-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
  font-size: 0.9rem;
}

.field-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.hint {
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
  margin: 0;
}

.warning {
  color: var(--p-red-500);
  font-weight: 500;
}

/* Fade transition for action buttons */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
