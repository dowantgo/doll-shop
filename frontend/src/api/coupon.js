import request from '../utils/request'

export const couponApi = {
  getMyCoupons(params) {
    return request.get('/coupons/my/', { params })
  },
  claimCoupon(data) {
    return request.post('/coupons/claim/', data)
  },
  pricePreview(data) {
    return request.post('/orders/price-preview/', data)
  },
  applyCoupon(orderId, data) {
    return request.post(`/orders/${orderId}/apply-coupon/`, data)
  },

  // Admin
  getCouponTemplates(params) {
    return request.get('/admin/coupon-templates/', { params })
  },
  createCouponTemplate(data) {
    return request.post('/admin/coupon-templates/', data)
  },
  updateCouponTemplate(id, data) {
    return request.put(`/admin/coupon-templates/${id}/`, data)
  },
  deleteCouponTemplate(id) {
    return request.delete(`/admin/coupon-templates/${id}/`)
  },
  issueCoupons(data) {
    return request.post('/admin/coupon-issue/', data)
  }
}
