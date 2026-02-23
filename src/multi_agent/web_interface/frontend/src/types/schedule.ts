/**
 * Schedule-related types for action plans
 */

export type ScheduleType = 'minutes' | 'hours' | 'weeks'

export interface ScheduleInfo {
  schedule_id: string
  name: string
  project_dir: string
  agent_name: string
  message: string
  schedule_type: ScheduleType
  interval_value: number
  start_from: string | null
  enabled: boolean
  last_run_at: string | null
  next_run_at: string | null
  created_at: string
  updated_at: string
}

export interface CreateScheduleRequest {
  name: string
  agent_name: string
  message: string
  schedule_type: ScheduleType
  interval_value: number
  start_from?: string | null
  enabled?: boolean
}

export interface UpdateScheduleRequest {
  name?: string
  agent_name?: string
  message?: string
  schedule_type?: ScheduleType
  interval_value?: number
  start_from?: string | null
  enabled?: boolean
}
