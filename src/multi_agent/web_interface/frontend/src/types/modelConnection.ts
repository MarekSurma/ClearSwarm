export interface ModelConnectionInfo {
  connection_id: string
  name: string
  base_url: string
  model: string
  has_api_key: boolean
  created_at: string
  updated_at: string
}

export interface CreateModelConnectionRequest {
  name: string
  base_url: string
  model?: string
  api_key?: string
}

export interface UpdateModelConnectionRequest {
  name?: string
  base_url?: string
  model?: string
  api_key?: string
}

export interface CloneModelConnectionRequest {
  new_name: string
}

export interface ListModelsRequest {
  connection_id?: string
  api_key?: string
  base_url?: string
}

export interface ListModelsResponse {
  models: string[]
}
