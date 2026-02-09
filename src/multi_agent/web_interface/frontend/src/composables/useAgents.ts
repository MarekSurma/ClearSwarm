import { ref } from 'vue'
import type { AgentInfo } from '@/types/agent'
import { useApi } from './useApi'

const agents = ref<AgentInfo[]>([])

export function useAgents() {
  const api = useApi()

  async function loadAgents() {
    try {
      agents.value = await api.getAgents()
    } catch (error) {
      console.error('Failed to load agents:', error)
    }
  }

  return { agents, loadAgents }
}
