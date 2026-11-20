export interface InventoryResponse {
  product_id: number
  quantity_on_hand: number
}

export interface InventoryInitRequest {
  product_id: number
  quantity: number
}

export interface InventoryAdjustRequest {
  product_id: number
  change_quantity: number
}

export type InventoryLogType =
  | 'INIT'
  | 'SALE'
  | 'RESTOCK'
  | 'ADJUSTMENT'
  | 'RETURN'

export interface InventoryLogResponse {
  id: number
  product_id: number
  change_quantity: number
  quantity_before: number
  quantity_after: number
  log_type: InventoryLogType
  reference_id: number | null
  log_date: string
}

export interface ListInventoryLogsParams {
  product_id?: number
  log_type?: InventoryLogType
  limit?: number
  offset?: number
}
