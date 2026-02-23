import { ref } from 'vue'
import type { ScheduleInfo } from '@/types/schedule'
import { useApi } from './useApi'

const schedules = ref<ScheduleInfo[]>([])

export function useSchedules() {
  const api = useApi()

  async function loadSchedules() {
    try {
      schedules.value = await api.getSchedules()
    } catch (error) {
      console.error('Failed to load schedules:', error)
    }
  }

  return { schedules, loadSchedules }
}
