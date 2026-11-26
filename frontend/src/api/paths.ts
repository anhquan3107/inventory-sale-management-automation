export const API_PATHS = {
  AUTH: {
    LOGIN: '/auth/login',
    ME: '/auth/me',
    CHANGE_PASSWORD: '/auth/change-password',
  },
  PRODUCTS: {
    LIST: '/products/',
    CREATE: '/products/',
    BY_ID: (productId: number) => `/products/${productId}`,
  },
  INVENTORY: {
    LIST: '/inventory/',
    INIT: '/inventory/init',
    ADJUST: '/inventory/adjust',
    BY_PRODUCT: (productId: number) => `/inventory/${productId}`,
  },
  INVENTORY_LOG: {
    LIST: '/inventory/logs',
  },
  SALES: {
    CREATE: '/sales/',
    LIST: '/sales',
    BY_ID: (orderId: number) => `/sales/${orderId}`,
  },
  DASHBOARD: {
    SUMMARY: '/dashboard/summary',
    REVENUE_TREND: '/dashboard/revenue-trend',
    TOP_PRODUCTS: '/dashboard/top-products',
    LOW_STOCK: '/dashboard/low-stock',
    RECENT_SALES: '/dashboard/recent-sales',
  },
  FORECAST: {
    ACCURACY: '/forecast/accuracy',
    PREDICTIONS: '/forecast/predictions',
    GENERATE: '/forecast/generate',
    COVERAGE: '/forecast/coverage',
    PRODUCT_COVERAGE: (productId: number) => `/forecast/coverage/${productId}`,
  },
  DECISIONS: {
    POLICIES: '/decisions/policies',
    POLICY: (productId: number) => `/decisions/policies/${productId}`,
    GENERATE: '/decisions/generate',
    EXCEPTIONS: '/decisions/exceptions',
    RECOMMENDATIONS: '/decisions/recommendations',
    RECOMMENDATION: (id: number) => `/decisions/recommendations/${id}`,
  },
}
