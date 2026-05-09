import request from '../utils/request'

export const orderApi = {
  getOrders(params) {
    return request.get('/orders/orders/', { params })
  },

  getOrderDetail(id) {
    return request.get(`/orders/orders/${id}/`)
  },

  createOrder(data, idempotencyKey) {
    return request.post('/orders/orders/create_from_cart/', data, {
      headers: idempotencyKey
        ? {
            'X-Idempotency-Key': idempotencyKey
          }
        : {}
    })
  },

  cancelOrder(id) {
    return request.post(`/orders/orders/${id}/cancel/`)
  },

  shipOrder(id) {
    return request.post(`/orders/orders/${id}/ship/`)
  },

  confirmDelivery(id) {
    return request.post(`/orders/orders/${id}/confirm_delivery/`)
  },

  getLogistics(id) {
    return request.get(`/orders/${id}/logistics/`)
  }
}
