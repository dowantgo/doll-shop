import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/userStore'

const routes = [
  {
    path: '/',
    component: () => import('../views/Home.vue'),
    name: 'Home',
    meta: { public: true }
  },
  {
    path: '/product/:id',
    component: () => import('../views/ProductDetail.vue'),
    name: 'ProductDetail',
    meta: { public: true }
  },
  {
    path: '/cart',
    component: () => import('../views/Cart.vue'),
    name: 'Cart',
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    component: () => import('../views/Login.vue'),
    name: 'Login',
    meta: { public: true, guestOnly: true }
  },
  {
    path: '/register',
    component: () => import('../views/Register.vue'),
    name: 'Register',
    meta: { public: true, guestOnly: true }
  },
  {
    path: '/orders',
    component: () => import('../views/Orders.vue'),
    name: 'Orders',
    meta: { requiresAuth: true }
  },
  {
    path: '/account',
    component: () => import('../views/Account.vue'),
    name: 'Account',
    meta: { requiresAuth: true }
  },
  {
    path: '/order/:id',
    component: () => import('../views/OrderDetail.vue'),
    name: 'OrderDetail',
    meta: { requiresAuth: true }
  },
  {
    path: '/forgot-password',
    component: () => import('../views/ForgotPassword.vue'),
    name: 'ForgotPassword',
    meta: { public: true, guestOnly: true }
  },
  {
    path: '/admin',
    component: () => import('../views/Admin.vue'),
    name: 'Admin',
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', component: () => import('../components/admin/DashboardView.vue') },
      { path: 'products', component: () => import('../components/admin/ProductManageView.vue') },
      { path: 'categories', component: () => import('../components/admin/CategoryManageView.vue') },
      { path: 'orders', component: () => import('../components/admin/OrderManageView.vue') },
      { path: 'inventory', component: () => import('../components/admin/InventoryManageView.vue') },
      { path: 'users', component: () => import('../components/admin/UserManageView.vue') }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const isLoggedIn = userStore.isLoggedIn()
  const user = userStore.user

  // Check if route requires authentication
  if (to.meta.requiresAuth && !isLoggedIn) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }

  // Check if route requires admin role
  if (to.meta.requiresAdmin && user?.role !== 'admin') {
    next({ name: 'Home' })
    return
  }

  // Check if route is guest only (login/register) and user is already logged in
  if (to.meta.guestOnly && isLoggedIn) {
    next({ name: 'Home' })
    return
  }

  next()
})

export default router
