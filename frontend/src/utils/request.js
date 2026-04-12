import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  // Default to Vite proxy in local dev; can be overridden by VITE_API_BASE_URL.
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/',
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json'
  }
})

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
  error => {
    const status = error.response?.status
    const data = error.response?.data

    if (status === 401) {
      const hasToken = !!localStorage.getItem('token')
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
