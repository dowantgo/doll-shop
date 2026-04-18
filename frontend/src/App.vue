<template>
  <div id="app">
    <nav class="navbar" v-if="!isAdminRoute">
      <div class="nav-brand" @click="router.push('/')">🎁 玩偶商城</div>
      <div class="nav-links">
        <router-link to="/" class="nav-link">首页</router-link>
        <router-link to="/seckill" class="nav-link">秒杀专区</router-link>
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
          <el-button v-if="user?.role === 'admin'" type="warning" size="small" @click="goAdmin">
            管理后台
          </el-button>
          <el-button type="danger" size="small" @click="logout">退出登录</el-button>
        </template>
      </div>
    </nav>

    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ShoppingCart, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { cartApi } from './api/cart'
import { useUserStore } from './stores/userStore'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const isLoggedIn = computed(() => userStore.isLoggedIn())
const user = computed(() => userStore.user)
const cartCount = ref(0)
const isAdminRoute = computed(() => route.path.startsWith('/admin'))

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
  if (!isLoggedIn.value) {
    cartCount.value = 0
    return
  }
  try {
    const res = await cartApi.getCart()
    cartCount.value = Number(res?.total_quantity || 0)
  } catch {
    cartCount.value = 0
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

:root {
  --bg-page: linear-gradient(160deg, #fff7f1 0%, #f5fbff 42%, #f7f8ff 100%);
  --card-bg: #ffffff;
  --brand-1: #ff8f3d;
  --brand-2: #2d8cff;
  --brand-3: #19b3a6;
  --text-main: #1f2a37;
  --text-sub: #5f6b7a;
  --line-soft: #e7edf5;
  --shadow-soft: 0 10px 30px rgba(39, 63, 99, 0.08);
}

body {
  font-family: "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
  background: var(--bg-page);
  color: var(--text-main);
  min-height: 100vh;
}

.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 28px;
  height: 68px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--line-soft);
  box-shadow: 0 8px 24px rgba(17, 24, 39, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-brand {
  font-size: 24px;
  font-weight: 800;
  background: linear-gradient(135deg, var(--brand-1), var(--brand-2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  cursor: pointer;
  letter-spacing: 0.5px;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.nav-link {
  text-decoration: none;
  color: var(--text-sub);
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 999px;
  transition: all 0.2s ease;
}

.nav-link:hover,
.nav-link.router-link-active {
  color: #1f4fa3;
  background: #eef5ff;
}

.main-content {
  max-width: 1320px;
  margin: 0 auto;
  padding: 22px 18px 28px;
}

.el-card {
  border: 1px solid var(--line-soft);
  box-shadow: var(--shadow-soft);
  border-radius: 14px;
}

.el-button {
  border-radius: 10px;
  font-weight: 600;
  letter-spacing: 0.2px;
  transition: all 0.2s ease;
}

.el-button--default {
  color: #34465a;
  border-color: #d4deeb;
  background: #ffffff;
}

.el-button--default:hover,
.el-button--default:focus {
  color: #1f4fa3;
  border-color: #bfd3ef;
  background: #f7fbff;
}

.el-button--primary:not(.is-text):not(.is-link):not(.is-plain) {
  color: #ffffff;
  border: none;
  background: linear-gradient(135deg, #2d8cff, #4f7cff);
  box-shadow: 0 8px 16px rgba(58, 115, 255, 0.22);
}

.el-button--primary:not(.is-text):not(.is-link):not(.is-plain):hover {
  background: linear-gradient(135deg, #1f7fff, #668cff);
}

.el-button--success:not(.is-text):not(.is-link):not(.is-plain) {
  color: #ffffff;
  border: none;
  background: linear-gradient(135deg, #20b26b, #40c987);
  box-shadow: 0 8px 16px rgba(32, 178, 107, 0.2);
}

.el-button--success:not(.is-text):not(.is-link):not(.is-plain):hover {
  background: linear-gradient(135deg, #15a55f, #37c47e);
}

.el-button--warning:not(.is-text):not(.is-link):not(.is-plain) {
  color: #ffffff;
  border: none;
  background: linear-gradient(135deg, #f5a623, #ffbf47);
  box-shadow: 0 8px 16px rgba(245, 166, 35, 0.2);
}

.el-button--warning:not(.is-text):not(.is-link):not(.is-plain):hover {
  background: linear-gradient(135deg, #ea990f, #ffb732);
}

.el-button--danger:not(.is-text):not(.is-link):not(.is-plain) {
  color: #ffffff;
  border: none;
  background: linear-gradient(135deg, #ff654f, #ff8a5a);
  box-shadow: 0 8px 16px rgba(255, 111, 76, 0.2);
}

.el-button--danger:not(.is-text):not(.is-link):not(.is-plain):hover {
  color: #ffffff;
  background: linear-gradient(135deg, #ff5740, #ff7d4f);
}

.el-button--info:not(.is-text):not(.is-link):not(.is-plain) {
  color: #ffffff;
  border: none;
  background: linear-gradient(135deg, #6d7f95, #8c9cb1);
  box-shadow: 0 8px 16px rgba(109, 127, 149, 0.2);
}

.el-button--info:not(.is-text):not(.is-link):not(.is-plain):hover {
  background: linear-gradient(135deg, #5f7289, #8192a8);
}

.el-button.is-plain {
  box-shadow: none;
}

.el-button--primary.is-plain {
  color: #1f5ed1;
  border-color: #bcd6ff;
  background: #eef5ff;
}

.el-button--primary.is-plain:hover {
  color: #1b4dad;
  background: #e1efff;
  border-color: #9fc3ff;
}

.el-button--danger.is-plain {
  color: #c7301a;
  border-color: #ffc5bb;
  background: #fff1ee;
}

.el-button--danger.is-plain:hover {
  color: #a92410;
  background: #ffe8e2;
  border-color: #ffad9f;
}

.el-button--warning.is-plain {
  color: #b06a00;
  border-color: #ffd89b;
  background: #fff5e6;
}

.el-button--warning.is-plain:hover {
  color: #915800;
  background: #ffeecf;
  border-color: #ffc969;
}

.el-button--success.is-plain {
  color: #198f56;
  border-color: #bde8d0;
  background: #ebfbf2;
}

.el-button--success.is-plain:hover {
  color: #147947;
  background: #def6ea;
  border-color: #9cddb9;
}

.el-button--info.is-plain {
  color: #4e5f74;
  border-color: #cdd8e4;
  background: #f2f6fa;
}

.el-button--info.is-plain:hover {
  color: #3f4f63;
  border-color: #b8c7d8;
  background: #eaf0f7;
}

.el-button.is-text,
.el-button.is-link {
  box-shadow: none !important;
  border: none !important;
  background: transparent !important;
}

.el-button--primary.is-text,
.el-button--primary.is-link {
  color: #1f5ed1 !important;
}

.el-button--danger.is-text,
.el-button--danger.is-link {
  color: #c7301a !important;
}

.el-button--warning.is-text,
.el-button--warning.is-link {
  color: #b06a00 !important;
}

.el-button--success.is-text,
.el-button--success.is-link {
  color: #198f56 !important;
}

.el-button--info.is-text,
.el-button--info.is-link {
  color: #4e5f74 !important;
}

.el-button.is-text:hover,
.el-button.is-link:hover {
  background: #f2f6fd !important;
}

.el-button--danger.is-text:hover,
.el-button--danger.is-link:hover {
  background: #ffece7 !important;
}

.el-button--warning.is-text:hover,
.el-button--warning.is-link:hover {
  background: #fff3df !important;
}

.el-button--success.is-text:hover,
.el-button--success.is-link:hover {
  background: #eaf9f1 !important;
}

.el-button.is-disabled,
.el-button.is-disabled:hover,
.el-button.is-disabled:focus {
  opacity: 0.58;
  filter: saturate(80%);
  box-shadow: none !important;
}

.el-input__wrapper,
.el-textarea__inner,
.el-select__wrapper {
  border-radius: 10px;
}

.el-table {
  --el-table-border-color: #e7edf5;
  --el-table-header-bg-color: #f8fbff;
}

@media (max-width: 900px) {
  .navbar {
    height: auto;
    padding: 12px 14px;
    gap: 10px;
    align-items: flex-start;
    flex-direction: column;
  }

  .nav-brand {
    font-size: 22px;
  }

  .nav-links {
    width: 100%;
    gap: 8px;
  }

  .main-content {
    padding: 14px 12px 20px;
  }
}
</style>
