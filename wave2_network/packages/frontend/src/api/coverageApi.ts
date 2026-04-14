import { apiClient } from './client'

export async function listCoverage() {
  return apiClient.get('/v1/coverage/stub')
}
