import axios from 'axios'
import { ElMessage } from 'element-plus'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/'

const api = axios.create({
  baseURL,
  timeout: 5000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

const refreshClient = axios.create({
  baseURL,
  timeout: 5000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

let refreshPromise = null

api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

api.interceptors.response.use(
  response => response.data,
  async error => {
    const status = error.response?.status
    const data = error.response?.data
    const originalRequest = error.config || {}

    if (status === 401) {
      const hasToken = !!localStorage.getItem('token')
      const isRefreshRequest = originalRequest.url?.includes('/users/users/refresh-token/')
      const isLoginRequest = originalRequest.url?.includes('/users/users/login/')
      const isLogoutRequest = originalRequest.url?.includes('/users/users/logout/')

      if (hasToken && !originalRequest._retry && !isRefreshRequest && !isLoginRequest && !isLogoutRequest) {
        originalRequest._retry = true
        try {
          refreshPromise =
            refreshPromise ||
            refreshClient.post('/users/users/refresh-token/').then(res => res.data).finally(() => {
              refreshPromise = null
            })
          const refreshData = await refreshPromise
          const newToken = refreshData?.access_token || refreshData?.token
          if (!newToken) throw new Error('refresh token response missing access token')
          localStorage.setItem('token', newToken)
          originalRequest.headers = originalRequest.headers || {}
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return api(originalRequest)
        } catch (_refreshError) {
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          ElMessage.error('登录状态已失效，请重新登录')
          window.location.href = '/login'
          return Promise.reject(error)
        }
      }

      if (hasToken) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        ElMessage.error('登录状态已失效，请重新登录')
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }

    if (status === 403) {
      ElMessage.error('没有权限执行此操作')
      return Promise.reject(error)
    }

    return Promise.reject({
      response: {
        data,
        status
      },
      message: error.message
    })
  }
)

export default api
