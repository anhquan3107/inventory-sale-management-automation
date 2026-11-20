import axiosInstance from '../api/axios'
import { API_PATHS } from '../api/paths'
import type {
  DashboardSummaryResponse,
  LowStockItem,
  RecentSaleItem,
  RevenueTrendItem,
  TopProductItem,
} from '../types/dashboard'

export const dashboardApi = {
  getSummary: async (): Promise<DashboardSummaryResponse> => {
    const response = await axiosInstance.get(API_PATHS.DASHBOARD.SUMMARY)
    return response.data
  },

  getRevenueTrend: async (days = 7): Promise<RevenueTrendItem[]> => {
    const response = await axiosInstance.get(API_PATHS.DASHBOARD.REVENUE_TREND, {
      params: { days },
    })
    return response.data
  },

  getTopProducts: async (limit = 5): Promise<TopProductItem[]> => {
    const response = await axiosInstance.get(API_PATHS.DASHBOARD.TOP_PRODUCTS, {
      params: { limit },
    })
    return response.data
  },

  getLowStock: async (): Promise<LowStockItem[]> => {
    const response = await axiosInstance.get(API_PATHS.DASHBOARD.LOW_STOCK)
    return response.data
  },

  getRecentSales: async (limit = 5): Promise<RecentSaleItem[]> => {
    const response = await axiosInstance.get(API_PATHS.DASHBOARD.RECENT_SALES, {
      params: { limit },
    })
    return response.data
  },
}
