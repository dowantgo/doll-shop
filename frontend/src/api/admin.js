import request from '../utils/request'

export const adminApi = {
  // Stats
  getStats() {
    return request.get('/admin/stats/')
  },

  // Products
  getProducts(params) {
    return request.get('/admin/products/', { params })
  },
  createProduct(data) {
    return request.post('/admin/products/', data)
  },
  updateProduct(id, data) {
    return request.put(`/admin/products/${id}/`, data)
  },
  deleteProduct(id) {
    return request.delete(`/admin/products/${id}/`)
  },
  uploadProductImage(productId, formData) {
    return request.post(`/admin/products/${productId}/upload-image/`, formData)
  },
  deleteProductImage(productId, imageId) {
    return request.delete(`/admin/products/${productId}/delete-image/${imageId}/`)
  },
  setMainProductImage(productId, imageId) {
    return request.post(`/admin/products/${productId}/set-main-image/${imageId}/`)
  },

  // Categories
  getCategories() {
    return request.get('/admin/categories/')
  },
  getCategoryProductCount(id) {
    return request.get(`/admin/categories/${id}/product_count/`)
  },
  createCategory(data) {
    return request.post('/admin/categories/', data)
  },
  updateCategory(id, data) {
    return request.put(`/admin/categories/${id}/`, data)
  },
  deleteCategory(id) {
    return request.delete(`/admin/categories/${id}/`)
  },

  // Orders
  getOrders(params) {
    return request.get('/admin/orders/', { params })
  },
  shipOrder(id) {
    return request.post(`/admin/orders/${id}/ship/`)
  },
  cancelOrder(id) {
    return request.post(`/admin/orders/${id}/cancel/`)
  },
  completeOrder(id) {
    return request.post(`/admin/orders/${id}/complete/`)
  },
  updateShipping(id, data) {
    return request.patch(`/orders/orders/${id}/update_shipping/`, data)
  },

  // Inventory
  adjustStock(id, data) {
    return request.post(`/admin/products/${id}/adjust_stock/`, data)
  },

  // Users
  getUsers(params) {
    return request.get('/admin/users/', { params })
  },
  setUserAdmin(id) {
    return request.post(`/admin/users/${id}/set_admin/`)
  },
  setUserRole(id) {
    return request.post(`/admin/users/${id}/set_user/`)
  },
  disableUser(id) {
    return request.post(`/admin/users/${id}/disable/`)
  },
  enableUser(id) {
    return request.post(`/admin/users/${id}/enable/`)
  }
}
