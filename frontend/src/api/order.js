import request from '../utils/request'

export const orderApi = {
  // Get orders
  getOrders(params) {
    return request.get('/orders/orders/', { params })
  },

  // Get order detail
  getOrderDetail(id) {
    return request.get(`/orders/orders/${id}/`)
  },

  // Create order from cart
  createOrder(data) {
    return request.post('/orders/orders/create_from_cart/', data)
  },

  // Cancel order
  cancelOrder(id) {
    return request.post(`/orders/orders/${id}/cancel/`)
  },

  // Ship order (admin)
  shipOrder(id) {
    return request.post(`/orders/orders/${id}/ship/`)
  },

  // Confirm delivery
  confirmDelivery(id) {
    return request.post(`/orders/orders/${id}/confirm_delivery/`)
  },

  // Logistics timeline
  getLogistics(id) {
    return request.get(`/orders/${id}/logistics/`)
  }
}
