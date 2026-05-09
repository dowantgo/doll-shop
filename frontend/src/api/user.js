import request from '../utils/request'

export const userApi = {
  getCaptcha() {
    return request.get('/users/users/captcha/')
  },

  sendEmailCode(email, type = 'register') {
    return request.post('/users/users/send_email_code/', { email, type })
  },

  register(data) {
    return request.post('/users/users/register/', data)
  },

  login(data) {
    return request.post('/users/users/login/', data)
  },

  refreshToken() {
    return request.post('/users/users/refresh-token/')
  },

  logout() {
    return request.post('/users/users/logout/')
  },

  forgotPassword(data) {
    return request.post('/users/users/forgot_password/', data)
  },

  getUserInfo() {
    return request.get('/users/users/me/')
  },

  getAddresses() {
    return request.get('/users/addresses/')
  },

  createAddress(data) {
    return request.post('/users/addresses/', data)
  },

  updateAddress(id, data) {
    return request.put(`/users/addresses/${id}/`, data)
  },

  deleteAddress(id) {
    return request.delete(`/users/addresses/${id}/`)
  }
}
