<template>
  <div class="admin-layout">
    <aside class="sidebar">
      <div class="logo">
        <h2>玩偶商城后台</h2>
      </div>
      <el-menu
        :default-active="activeMenu"
        class="admin-menu"
        router
        background-color="transparent"
        text-color="#d5e3f8"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/admin/dashboard">
          <el-icon><DataLine /></el-icon>
          <span>数据概览</span>
        </el-menu-item>
        <el-menu-item index="/admin/products">
          <el-icon><Goods /></el-icon>
          <span>商品管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/categories">
          <el-icon><Folder /></el-icon>
          <span>分类管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/orders">
          <el-icon><List /></el-icon>
          <span>订单管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/seckill">
          <el-icon><Timer /></el-icon>
          <span>秒杀管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/coupons">
          <el-icon><Ticket /></el-icon>
          <span>优惠券管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/refunds">
          <el-icon><Money /></el-icon>
          <span>退款审核</span>
        </el-menu-item>
        <el-menu-item index="/admin/inventory">
          <el-icon><Box /></el-icon>
          <span>库存管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
      </el-menu>
    </aside>

    <div class="main-content">
      <header class="admin-header">
        <div class="header-left">
          <span class="welcome">欢迎，{{ userStore.user?.username || '管理员' }}</span>
        </div>
        <div class="header-right">
          <el-button type="primary" text @click="goToFrontend">
            <el-icon><HomeFilled /></el-icon>
            返回前台
          </el-button>
          <el-button type="danger" text @click="logout">
            <el-icon><SwitchButton /></el-icon>
            退出登录
          </el-button>
        </div>
      </header>

      <main class="admin-main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Box,
  DataLine,
  Folder,
  Goods,
  HomeFilled,
  List,
  Money,
  SwitchButton,
  Ticket,
  Timer,
  User
} from '@element-plus/icons-vue'
import { useUserStore } from '../stores/userStore'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)

const goToFrontend = () => {
  router.push('/')
}

const logout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(() => {
      userStore.logout()
      ElMessage.success('已退出登录')
      router.push('/login')
    })
    .catch(() => {})
}
</script>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 228px;
  background: linear-gradient(180deg, #173453 0%, #1f3f63 48%, #173454 100%);
  position: fixed;
  height: 100vh;
  left: 0;
  top: 0;
  z-index: 100;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}

.logo {
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo h2 {
  margin: 0;
  font-size: 19px;
  letter-spacing: 0.4px;
}

.admin-menu {
  border-right: none;
  padding-top: 8px;
}

.admin-menu :deep(.el-menu-item) {
  margin: 6px 10px;
  border-radius: 10px;
  height: 44px;
  line-height: 44px;
}

.admin-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.1) !important;
}

.admin-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, #2f7cff, #4f95ff) !important;
}

.main-content {
  flex: 1;
  margin-left: 228px;
  background: linear-gradient(155deg, #f6fbff 0%, #f8f7ff 52%, #fff9f5 100%);
  min-height: 100vh;
}

.admin-header {
  height: 66px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid #e6edf7;
  position: sticky;
  top: 0;
  z-index: 99;
}

.welcome {
  font-size: 14px;
  color: #44566c;
  font-weight: 600;
}

.header-right {
  display: flex;
  gap: 8px;
}

.admin-main {
  padding: 18px;
}

@media (max-width: 960px) {
  .sidebar {
    width: 86px;
  }

  .logo h2 {
    font-size: 12px;
    text-align: center;
    line-height: 1.2;
    padding: 0 4px;
  }

  .main-content {
    margin-left: 86px;
  }
}
</style>
