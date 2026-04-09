import request from '../utils/request'

export const paymentApi = {
  createPayment(orderId, paymentMethod) {
    return request.post('/pay/create_payment/', {
      order_id: orderId,
      payment_method: paymentMethod
    })
  },

  getStatus(paymentId) {
    return request.get(`/pay/${paymentId}/status/`)
  },

  closePayment(paymentId) {
    return request.post(`/pay/${paymentId}/close/`)
  },

  mockPay(paymentId) {
    return request.post(`/pay/${paymentId}/mock_pay/`)
  }
}
