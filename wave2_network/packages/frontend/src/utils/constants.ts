export const APP_NAME = 'Blindference Wave 2'

export const SIGNAL_ASSETS = ['ETH', 'BTC', 'SOL'] as const
export const MODEL_OPTIONS = [
  { value: 'groq:llama3-70b', label: 'Groq · Llama 3 70B' },
  { value: 'gemini:gemini-pro', label: 'Google Gemini Pro' },
] as const
