<template>
  <div class="home">
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索商品（名称/描述）"
        class="search"
        clearable
        @keyup.enter="onSearch"
      />
      <el-button type="primary" :loading="loading" @click="onSearch">搜索</el-button>
      <el-button text @click="resetFilter">重置</el-button>
    </div>

    <div class="content">
      <aside class="sidebar">
        <el-card shadow="never">
          <template #header>
            <div>分类</div>
          </template>
          <div class="cat-list">
            <el-button
              v-for="cat in categories"
              :key="cat.id"
              :type="cat.id === selectedCategoryId ? 'primary' : 'default'"
              size="small"
              class="cat-btn"
              @click="selectCategory(cat.id)"
            >
              {{ cat.name }}
            </el-button>
            <el-button
              v-if="categories.length"
              :type="selectedCategoryId === null ? 'primary' : 'default'"
              size="small"
              class="cat-btn"
              @click="selectedCategoryId = null; loadHot()"
            >
              热门
            </el-button>
          </div>
        </el-card>
      </aside>

      <main class="main">
        <div v-if="loading" class="loading">加载中...</div>

        <el-empty v-else-if="products.length === 0" description="暂无商品" />

        <el-row :gutter="16">
          <el-col v-for="p in products" :key="p.id" :span="6">
            <el-card shadow="never" class="product-card" :body-style="{ padding: 0 }">
              <div class="img-wrap" @click="goDetail(p.id)">
                <img class="img" :src="getMainImage(p)" alt="" />
              </div>
              <div class="product-body">
                <div class="title" :title="p.name">{{ p.name }}</div>
                <div class="meta">
                  <span class="price">￥{{ p.price }}</span>
                  <span class="stock">库存：{{ p.stock }}</span>
                </div>
                <div class="actions">
                  <el-button size="small" @click="goDetail(p.id)">详情</el-button>
                  <el-button
                    size="small"
                    type="primary"
                    @click="addToCart(p.id)"
                  >
                    加入购物车
                  </el-button>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </main>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { productApi } from '../api/product'
import { cartApi } from '../api/cart'

const router = useRouter()

const keyword = ref('')
const loading = ref(false)
const categories = ref([])
const selectedCategoryId = ref(null)
const products = ref([])

const loadCategories = async () => {
  const res = await productApi.getCategories()
  categories.value = res?.results || res || []
}

const pickMainImage = product => {
  const imgs = product?.images || []
  const main = imgs.find(i => i.is_main) || imgs[0]
  return main?.image_url || main?.image?.url || ''
}

const getMainImage = p => {
  // Some records may not have images; keep img src empty to avoid console noise.
  return pickMainImage(p)
}

const loadHot = async () => {
  loading.value = true
  try {
    const res = await productApi.getHotProducts()
    products.value = res || []
  } finally {
    loading.value = false
  }
}

const loadByCategory = async categoryId => {
  loading.value = true
  try {
    const res = await productApi.getProducts({ category: categoryId, status: true })
    products.value = res?.results || res || []
  } finally {
    loading.value = false
  }
}

const onSearch = async () => {
  const kw = keyword.value.trim()
  if (!kw) {
    selectedCategoryId.value = null
    return loadHot()
  }

  loading.value = true
  try {
    const res = await productApi.searchProducts(kw)
    products.value = res?.results || res || []
  } finally {
    loading.value = false
  }
}

const resetFilter = () => {
  keyword.value = ''
  selectedCategoryId.value = null
  loadHot()
}

const selectCategory = async id => {
  selectedCategoryId.value = id
  if (keyword.value.trim()) keyword.value = ''
  await loadByCategory(id)
}

const addToCart = async productId => {
  // Check if user is logged in
  const token = localStorage.getItem('token')
  if (!token) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }

  try {
    await cartApi.addToCart(productId, 1)
    ElMessage.success('已加入购物车')
  } catch (e) {
    // Error is handled by request interceptor (401 will redirect to login)
    if (e?.response?.status !== 401) {
      ElMessage.error(e?.response?.data?.error || '加入购物车失败')
    }
  }
}

const goDetail = id => {
  router.push(`/product/${id}`)
}

onMounted(async () => {
  await loadCategories()
  await loadHot()
})
</script>

<style scoped>
.home {
  padding: 18px;
}

.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.search {
  width: 420px;
}

.content {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 16px;
}

.cat-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.cat-btn {
  white-space: nowrap;
}

.img-wrap {
  height: 170px;
  overflow: hidden;
  cursor: pointer;
  background: #fafafa;
}

.img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-body {
  padding: 12px;
}

.title {
  font-weight: 600;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta {
  display: flex;
  justify-content: space-between;
  color: #666;
  font-size: 12px;
  margin-bottom: 10px;
}

.price {
  color: #ff4d4f;
  font-weight: 600;
}

.actions {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.loading {
  padding: 20px;
  color: #666;
}
</style>
