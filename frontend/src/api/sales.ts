import axiosInstance from '../api/axios'
import { API_PATHS } from '../api/paths'
import type {
  CreateSaleRequest,
  CreateSaleResponse,
  ListSalesParams,
  SaleDetailRead,
  SaleRead,
} from '../types/sales'

export const salesApi = {
  create: async (data: CreateSaleRequest): Promise<CreateSaleResponse> => {
    const response = await axiosInstance.post(API_PATHS.SALES.CREATE, data)
    return response.data
  },

  list: async (params: ListSalesParams = {}): Promise<SaleRead[]> => {
    const response = await axiosInstance.get(API_PATHS.SALES.LIST, { params })
    return response.data
  },

  getById: async (orderId: number): Promise<SaleDetailRead> => {
    const response = await axiosInstance.get(API_PATHS.SALES.BY_ID(orderId))
    return response.data
  },
}
