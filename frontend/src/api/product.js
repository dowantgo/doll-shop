import request from '../utils/request'

export const productApi = {
  normalizeListResponse(data) {
    if (Array.isArray(data)) return data
    if (Array.isArray(data?.results)) return data.results
    return []
  },

  // Get all products
  getProducts(params) {
    return request.get('/products/products/', { params })
  },

  // Get product detail
  getProductDetail(id) {
    return request.get(`/products/products/${id}/`)
  },

  // Get hot products
  getHotProducts() {
    return request.get('/products/products/hot_products/').then(data => this.normalizeListResponse(data))
  },

  // Top sales ranking (compat with legacy underscore route)
  async getTopSales(params) {
    try {
      const data = await request.get('/products/products/top-sales/', { params })
      return this.normalizeListResponse(data)
    } catch (error) {
      if (error?.response?.status === 404) {
        const data = await request.get('/products/products/top_sales/', { params })
        return this.normalizeListResponse(data)
      }
      throw error
    }
  },

  // Hot feed (compat with legacy underscore route)
  async getHotFeed(params) {
    try {
      const data = await request.get('/products/products/hot-feed/', { params })
      return this.normalizeListResponse(data)
    } catch (error) {
      if (error?.response?.status === 404) {
        const data = await request.get('/products/products/hot_feed/', { params })
        return this.normalizeListResponse(data)
      }
      throw error
    }
  },

  // Get categories
  getCategories() {
    return request.get('/products/categories/')
  },

  // Search products
  searchProducts(keyword) {
    return request.get('/products/products/', {
      params: { search: keyword }
    })
  }
}
