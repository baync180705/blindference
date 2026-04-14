import { apiClient } from './client'

export async function listNodes() {
  return apiClient.get('/v1/nodes/stub')
}
