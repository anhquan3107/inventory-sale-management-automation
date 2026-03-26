import axiosInstance from '../api/axios'
import { API_PATHS } from '../api/paths'
import type {
  CreateProductRequest,
  ProductResponse,
  UpdateProductRequest,
} from '../types/product'

export const productsApi = {
  list: async (): Promise<ProductResponse[]> => {
    const response = await axiosInstance.get(API_PATHS.PRODUCTS.LIST)
    return response.data
  },

  create: async (data: CreateProductRequest): Promise<ProductResponse> => {
    const response = await axiosInstance.post(API_PATHS.PRODUCTS.CREATE, data)
    return response.data
  },

  getById: async (productId: number): Promise<ProductResponse> => {
    const response = await axiosInstance.get(
      API_PATHS.PRODUCTS.BY_ID(productId),
    )
    return response.data
  },

  update: async (
    productId: number,
    data: UpdateProductRequest,
  ): Promise<ProductResponse> => {
    const response = await axiosInstance.patch(
      API_PATHS.PRODUCTS.BY_ID(productId),
      data,
    )
    return response.data
  },
}
