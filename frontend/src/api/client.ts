import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Health check
export const getHealthStatus = async () => {
  const response = await apiClient.get('/health')
  return response.data
}

// System status
export const getSystemStatus = async () => {
  const response = await apiClient.get('/status')
  return response.data
}

// Get available agents
export const getAvailableAgents = async () => {
  const response = await apiClient.get('/status')
  return response.data.agents || []
}

// Execute agent (placeholder - will be implemented with actual API)
export const executeAgent = async (agentName: string, inputData: any) => {
  const response = await apiClient.post('/api/agents/execute', {
    agent_name: agentName,
    input_data: inputData,
  })
  return response.data
}

// Get analysis results (placeholder)
export const getAnalysisResults = async () => {
  const response = await apiClient.get('/api/results')
  return response.data
}

// Get specific analysis (placeholder)
export const getAnalysis = async (id: number) => {
  const response = await apiClient.get(`/api/results/${id}`)
  return response.data
}

export default apiClient
