<template>
  <div id="app">
    <nav class="navbar" v-if="!isAdminRoute">
      <div class="nav-brand" @click="$router.push('/')">🎁 玩偶商城</div>
      <div class="nav-links">
        <router-link to="/" class="nav-link">首页</router-link>
        <router-link to="/cart" class="nav-link">
          <el-badge :value="cartCount" :hidden="cartCount === 0">
            <el-icon><ShoppingCart /></el-icon>
            购物车
          </el-badge>
        </router-link>
        <router-link to="/orders" class="nav-link">我的订单</router-link>
        <template v-if="!isLoggedIn">
          <router-link to="/login" class="nav-link">登录</router-link>
          <router-link to="/register" class="nav-link">注册</router-link>
        </template>
        <template v-else>
          <router-link to="/account" class="nav-link">
            <el-icon><User /></el-icon>
            {{ user?.username || '个人中心' }}
          </router-link>
          <el-button v-if="user?.role === 'admin'" type="warning" size="small" @click="goAdmin">管理后台</el-button>
          <el-button type="danger" size="small" @click="logout">退出</el-button>
        </template>
      </div>
    </nav>
    <main class="main-content">
      <router-view></router-view>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from './stores/userStore'
import { ShoppingCart, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { cartApi } from './api/cart'

const router = useRouter()
const userStore = useUserStore()

const isLoggedIn = computed(() => userStore.isLoggedIn())
const user = computed(() => userStore.user)
const cartCount = ref(0)
const isAdminRoute = computed(() => router.currentRoute.value.path.startsWith('/admin'))

const logout = () => {
  userStore.logout()
  cartCount.value = 0
  ElMessage.success('已退出登录')
  router.push('/')
}

const goAdmin = () => {
  router.push('/admin')
}

const loadCartCount = async () => {
  if (!isLoggedIn.value) return
  try {
    const res = await cartApi.getCart()
    cartCount.value = res?.total_quantity || 0
  } catch (e) {
    console.error('获取购物车数量失败', e)
  }
}

onMounted(() => {
  loadCartCount()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f5f5;
}

.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  height: 60px;
  background: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-brand {
  font-size: 20px;
  font-weight: bold;
  color: #409eff;
  cursor: pointer;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 24px;
}

.nav-link {
  text-decoration: none;
  color: #606266;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.nav-link:hover,
.nav-link.router-link-active {
  color: #409eff;
}

.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}
</style>
