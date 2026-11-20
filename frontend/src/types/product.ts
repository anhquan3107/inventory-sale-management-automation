export interface ProductResponse {
  id: number
  sku: string
  name: string
  category: string | null
  unit_price: string
  is_active: boolean
}

export interface CreateProductRequest {
  sku: string
  name: string
  category?: string | null
  unit_price: number
}

export interface UpdateProductRequest {
  name?: string
  category?: string | null
  unit_price?: number
  is_active?: boolean
}
