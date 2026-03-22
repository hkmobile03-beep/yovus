export interface Order {
  id: number
  order_no: string
  platform_order_no: string
  platform: string
  status: string
  total_amount: number
  product_amount: number
  freight_amount: number
  discount_amount: number
  commission_amount: number
  settlement_amount: number
  refund_amount: number
  order_time: string
  payment_time: string
  complete_time: string | null
  buyer_name: string
}

export interface ReconciliationTask {
  id: number
  task_no: string
  platform: string
  period: string
  status: string
  total_orders: number
  matched_orders: number
  discrepancy_orders: number
  match_rate: string
  total_diff_amount: number
  created_at: string
}

export interface ReconciliationRecord {
  id: number
  order_no: string
  status: string
  system_amount: number
  platform_amount: number
  amount_diff: number
  reason: string
}

export interface RevenueComparison {
  period: string
  basis1_revenue: number
  basis1_revenue_ex_tax: number
  basis1_tax: number
  basis1_order_count: number
  basis2_revenue: number
  basis2_revenue_ex_tax: number
  basis2_tax: number
  basis2_order_count: number
  difference: number
  difference_orders: number
}

export interface TaxDeclaration {
  period: string
  output_tax: number
  input_tax: number
  tax_payable: number
  carryforward: number
  surcharges: {
    urban_maintenance: number
    education: number
    local_education: number
    total: number
  }
}

export interface ProfitSummary {
  period: string
  total_revenue: number
  total_cost: number
  gross_profit: number
  gross_margin: number
  net_profit: number
  net_margin: number
  order_count: number
}

export interface SkuProfit {
  sku: string
  product_name: string
  quantity: number
  revenue: number
  cost: number
  profit: number
  margin: number
}

export interface PlatformROI {
  platform: string
  revenue: number
  commission: number
  promotion_cost: number
  logistics_cost: number
  refund_amount: number
  total_cost: number
  profit: number
  roi: number
}

export interface BudgetItem {
  id: number
  name: string
  budget_type: string
  period: string
  planned_amount: number
  actual_amount: number
  execution_rate: number
}

export interface AlertLog {
  id: number
  rule_name: string
  alert_level: string
  metric: string
  current_value: number
  threshold: number
  message: string
  status: string
  triggered_at: string
}

export interface AIAnalysisRequest {
  question: string
  context_type: 'orders' | 'reconciliation' | 'tax' | 'profit' | 'general'
  period?: string
}

export interface AIAnalysisResponse {
  analysis: string
  suggestions: string[]
  data_points: Record<string, number | string>[]
}

export interface DashboardMetrics {
  total_revenue: number
  total_orders: number
  avg_order_value: number
  refund_rate: number
  gross_margin: number
  tax_payable: number
  pending_reconciliation: number
  alert_count: number
  revenue_trend: { month: string; revenue: number; cost: number }[]
  platform_distribution: { name: string; value: number }[]
}
