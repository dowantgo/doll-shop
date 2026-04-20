import request from '../utils/request'

export const refundApi = {
  createRefund(data) {
    return request.post('/refunds/', data)
  },
  getMyRefunds(params) {
    return request.get('/refunds/my/', { params })
  },
  getRefundDetail(id) {
    return request.get(`/refunds/${id}/`)
  },

  // Admin
  getAdminRefunds(params) {
    return request.get('/admin/refunds/', { params })
  },
  reviewRefund(id, data) {
    return request.patch(`/admin/refunds/${id}/review/`, data)
  }
}
