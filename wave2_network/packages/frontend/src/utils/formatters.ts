export function formatNumber(value: number) {
  return new Intl.NumberFormat('en-US').format(value)
}

export function formatAddress(value: string) {
  if (value.length <= 10) return value
  return `${value.slice(0, 6)}...${value.slice(-4)}`
}

export function formatTimestamp(value?: string | null) {
  if (!value) return 'Pending'
  return new Date(value).toLocaleString()
}

export function formatTxUrl(txHash?: string | null) {
  if (!txHash) return null
  return `https://sepolia.arbiscan.io/tx/${txHash}`
}
