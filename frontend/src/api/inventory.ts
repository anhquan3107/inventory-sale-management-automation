import axiosInstance from '../api/axios'
import { API_PATHS } from '../api/paths'
import type {
  InventoryAdjustRequest,
  InventoryInitRequest,
  InventoryResponse,
} from '../types/inventory'

export const inventoryApi = {
  list: async (): Promise<InventoryResponse[]> => {
    const response = await axiosInstance.get(API_PATHS.INVENTORY.LIST)
    return response.data
  },

  getByProduct: async (productId: number): Promise<InventoryResponse> => {
    const response = await axiosInstance.get(
      API_PATHS.INVENTORY.BY_PRODUCT(productId),
    )
    return response.data
  },

  init: async (data: InventoryInitRequest): Promise<InventoryResponse> => {
    const response = await axiosInstance.post(API_PATHS.INVENTORY.INIT, data)
    return response.data
  },

  adjust: async (data: InventoryAdjustRequest): Promise<InventoryResponse> => {
    const response = await axiosInstance.put(API_PATHS.INVENTORY.ADJUST, data)
    return response.data
  },
}
