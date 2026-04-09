import { defineStore } from 'pinia'
import { ref } from 'vue'
import { userApi } from '../api/user'

export const useUserStore = defineStore('user', () => {
  const user = ref(JSON.parse(localStorage.getItem('user')) || null)
  const token = ref(localStorage.getItem('token') || null)

  const setUser = (userData, userToken) => {
    user.value = userData
    token.value = userToken
    localStorage.setItem('user', JSON.stringify(userData))
    localStorage.setItem('token', userToken)
  }

  const logout = () => {
    user.value = null
    token.value = null
    localStorage.removeItem('user')
    localStorage.removeItem('token')
  }

  const isLoggedIn = () => !!token.value

  return { user, token, setUser, logout, isLoggedIn }
})
