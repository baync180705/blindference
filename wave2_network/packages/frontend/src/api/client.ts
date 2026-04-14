import axios from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_ICL_API_URL ?? 'http://localhost:8000',
})
