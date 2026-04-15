export interface DashboardSummaryResponse {
  revenue_today: string
  revenue_month: string
  orders_today: number
  low_stock_count: number
}

export interface RevenueTrendItem {
  date: string
  revenue: string
}

export interface TopProductItem {
  product_id: number
  product_name: string
  total_quantity_sold: number
}

export interface LowStockItem {
  product_id: number
  product_name: string
  current_stock: number
}

export interface RecentSaleItem {
  sale_id: number
  total_amount: string
  sales_channel: string
  created_at: string
}
