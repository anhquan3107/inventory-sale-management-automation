export interface CreateSaleItemRequest {
  product_id: number
  quantity: number
  unit_price: number
}

export interface CreateSaleRequest {
  sales_channel: string
  items: CreateSaleItemRequest[]
}

export interface CreateSaleResponse {
  order_id: number
  total_amount: string
}

export interface SaleRead {
  id: number
  order_date: string
  sales_channel: string
  total_amount: string
}

export interface SaleItemRead {
  product_id: number
  quantity: number
  unit_price: string
  line_total: string
}

export interface SaleDetailRead {
  id: number
  order_date: string
  sales_channel: string
  total_amount: string
  items: SaleItemRead[]
}

export interface ListSalesParams {
  date_from?: string
  date_to?: string
  sales_channel?: string
  product_id?: number
}
