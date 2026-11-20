import axiosInstance from '../api/axios'
import { API_PATHS } from '../api/paths'
import type {
  InventoryLogResponse,
  ListInventoryLogsParams,
} from '../types/inventory'

export const inventoryLogApi = {
  list: async (
    params: ListInventoryLogsParams = {},
  ): Promise<InventoryLogResponse[]> => {
    const response = await axiosInstance.get(API_PATHS.INVENTORY_LOG.LIST, {
      params,
    })
    return response.data
  },
}
