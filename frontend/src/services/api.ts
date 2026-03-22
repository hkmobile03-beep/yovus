const BASE_URL = '/api/v1'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || '请求失败')
  }
  return res.json()
}

export const api = {
  // Dashboard
  getDashboard: (period?: string) =>
    request<any>(`/analytics/dashboard${period ? `?period=${period}` : ''}`),

  // Orders
  getOrders: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : ''
    return request<any>(`/orders${qs}`)
  },
  importOrders: (file: File, platform: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('platform', platform)
    return fetch(`${BASE_URL}/orders/import`, { method: 'POST', body: form }).then(r => r.json())
  },

  // Reconciliation
  getReconciliationTasks: () => request<any>('/reconciliation/tasks'),
  getReconciliationDetail: (taskId: number) =>
    request<any>(`/reconciliation/tasks/${taskId}`),
  startReconciliation: (data: any) =>
    request<any>('/reconciliation/start', { method: 'POST', body: JSON.stringify(data) }),

  // Revenue Calibration
  getRevenueComparison: (period: string) =>
    request<any>(`/revenue-calibration/compare?period=${period}`),

  // Tax
  getVATDeclaration: (period: string) =>
    request<any>(`/tax/vat/declaration?period=${period}`),
  getIncomeTax: (year: string) =>
    request<any>(`/tax/income?year=${year}`),

  // Platform Fees
  getPlatformFees: (period?: string) =>
    request<any>(`/platform-fees${period ? `?period=${period}` : ''}`),
  getFeeInvoiceStatus: (period?: string) =>
    request<any>(`/platform-fees/invoice-status${period ? `?period=${period}` : ''}`),

  // Analytics
  getProfitSummary: (period: string) =>
    request<any>(`/analytics/profit?period=${period}`),
  getSkuProfit: (period: string) =>
    request<any>(`/analytics/sku-profit?period=${period}`),
  getPlatformROI: (period: string) =>
    request<any>(`/analytics/platform-roi?period=${period}`),

  // Budget & Alerts
  getBudgets: (period?: string) =>
    request<any>(`/alerts/budgets${period ? `?period=${period}` : ''}`),
  getAlertLogs: () => request<any>('/alerts/logs'),

  // AI Analysis
  analyzeData: (data: any) =>
    request<any>('/ai/analyze', { method: 'POST', body: JSON.stringify(data) }),
}
