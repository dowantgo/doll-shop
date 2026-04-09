import request from '../utils/request'

export const productApi = {
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
    return request.get('/products/products/hot_products/')
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
