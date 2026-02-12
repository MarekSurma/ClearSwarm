/**
 * Project management composable with singleton state
 */
import { ref, computed, type Ref } from 'vue'
import type { ProjectInfo, CreateProjectRequest, CloneProjectRequest } from '../types/project'

// Module-level refs (shared singleton state)
const currentProject: Ref<ProjectInfo> = ref({
  project_name: 'default',
  project_dir: 'default',
  created_at: new Date().toISOString()
})

const projects: Ref<ProjectInfo[]> = ref([])
const pendingProject: Ref<ProjectInfo | null> = ref(null)

export function useProject() {
  // Computed properties
  const isDefault = computed(() => currentProject.value.project_dir === 'default')
  const hasPendingSwitch = computed(
    () => pendingProject.value !== null && pendingProject.value.project_dir !== currentProject.value.project_dir
  )

  /**
   * Load all projects from the API
   */
  async function loadProjects(): Promise<void> {
    try {
      const response = await fetch('/api/projects')
      if (!response.ok) {
        throw new Error(`Failed to load projects: ${response.statusText}`)
      }
      const data = await response.json()
      projects.value = data

      // Set current project to default if not already set
      const defaultProject = data.find((p: ProjectInfo) => p.project_dir === 'default')
      if (defaultProject && currentProject.value.project_dir === 'default') {
        currentProject.value = defaultProject
      }
    } catch (error) {
      console.error('Error loading projects:', error)
      throw error
    }
  }

  /**
   * Select a project (sets as pending, not immediately switched)
   */
  function selectProject(project: ProjectInfo): void {
    pendingProject.value = project
  }

  /**
   * Switch to the pending project
   */
  function switchProject(project: ProjectInfo | null = null): void {
    const targetProject = project || pendingProject.value
    if (!targetProject) return

    currentProject.value = targetProject
    pendingProject.value = null

    // Trigger reload event (components can listen to this)
    window.dispatchEvent(new CustomEvent('project-switched', { detail: targetProject }))
  }

  /**
   * Create a new project
   */
  async function createProject(request: CreateProjectRequest): Promise<ProjectInfo> {
    try {
      const response = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || `Failed to create project: ${response.statusText}`)
      }

      const newProject = await response.json()

      // Reload projects list
      await loadProjects()

      return newProject
    } catch (error) {
      console.error('Error creating project:', error)
      throw error
    }
  }

  /**
   * Clone an existing project
   */
  async function cloneProject(request: CloneProjectRequest): Promise<ProjectInfo> {
    try {
      const response = await fetch('/api/projects/clone', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || `Failed to clone project: ${response.statusText}`)
      }

      const newProject = await response.json()

      // Reload projects list
      await loadProjects()

      return newProject
    } catch (error) {
      console.error('Error cloning project:', error)
      throw error
    }
  }

  /**
   * Delete a project
   */
  async function deleteProject(projectName: string): Promise<void> {
    try {
      const response = await fetch(`/api/projects/${encodeURIComponent(projectName)}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || `Failed to delete project: ${response.statusText}`)
      }

      // If we deleted the current project, switch to default
      if (currentProject.value.project_name === projectName) {
        const defaultProj = projects.value.find(p => p.project_dir === 'default')
        if (defaultProj) {
          switchProject(defaultProj)
        }
      }

      // Reload projects list
      await loadProjects()
    } catch (error) {
      console.error('Error deleting project:', error)
      throw error
    }
  }

  return {
    // State
    currentProject,
    projects,
    pendingProject,

    // Computed
    isDefault,
    hasPendingSwitch,

    // Methods
    loadProjects,
    selectProject,
    switchProject,
    createProject,
    cloneProject,
    deleteProject
  }
}
