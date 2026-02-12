/**
 * Project-related type definitions
 */

export interface ProjectInfo {
  project_name: string
  project_dir: string
  created_at: string
}

export interface CreateProjectRequest {
  name: string
  create_tools: boolean
  create_prompts: boolean
}

export interface CloneProjectRequest {
  source_project_dir: string
  new_name: string
  clone_tools: boolean
  clone_prompts: boolean
}
