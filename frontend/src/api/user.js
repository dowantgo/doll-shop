import request from '../utils/request'

export const userApi = {
  // Get captcha image
  getCaptcha() {
    return request.get('/users/users/captcha/')
  },

  // Send email verification code
  sendEmailCode(email, type = 'register') {
    return request.post('/users/users/send_email_code/', { email, type })
  },

  // Register with captcha and email verification
  register(data) {
    return request.post('/users/users/register/', data)
  },

  // Login with captcha
  login(data) {
    return request.post('/users/users/login/', data)
  },

  // Forgot password
  forgotPassword(data) {
    return request.post('/users/users/forgot_password/', data)
  },

  // Get user info
  getUserInfo() {
    return request.get('/users/users/me/')
  },

  // Get addresses
  getAddresses() {
    return request.get('/users/addresses/')
  },

  // Create address
  createAddress(data) {
    return request.post('/users/addresses/', data)
  },

  // Update address
  updateAddress(id, data) {
    return request.put(`/users/addresses/${id}/`, data)
  },

  // Delete address
  deleteAddress(id) {
    return request.delete(`/users/addresses/${id}/`)
  }
}
