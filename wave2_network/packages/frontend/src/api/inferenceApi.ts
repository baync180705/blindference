import { apiClient } from './client'

export async function getInferenceStatus() {
  return apiClient.get('/health')
}
