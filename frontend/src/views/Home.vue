<template>
  <div class="home">
    <div class="hero-panel">
      <div class="hero-title">发现今日人气玩偶</div>
      <div class="hero-subtitle">热榜轮播 + 销量排行，支持按分类与关键词快速筛选</div>
      <div class="toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索商品（名称/描述）"
          class="search"
          clearable
          @keyup.enter="onSearch"
        />
        <el-button type="primary" :loading="loading" @click="onSearch">搜索</el-button>
        <el-button type="danger" plain @click="goSeckillZone">秒杀专区</el-button>
        <el-button text @click="resetFilter">重置</el-button>
      </div>
    </div>

    <div class="headline-grid">
      <el-card class="headline-card" shadow="never">
        <template #header>
          <div class="headline-title">热榜轮播</div>
        </template>
        <el-skeleton v-if="headlineLoading" :rows="4" animated />
        <el-alert
          v-else-if="headlineError"
          :title="headlineError"
          type="error"
          :closable="false"
          show-icon
        />
        <el-empty v-else-if="hotFeed.length === 0" description="暂无热榜" />
        <el-carousel
          v-else
          class="headline-carousel"
          height="340px"
          indicator-position="outside"
          autoplay
          :interval="3500"
        >
          <el-carousel-item v-for="item in hotFeed" :key="item.id">
            <div class="slide" @click="goDetail(item.id)">
              <img class="slide-img" :src="item.main_image || defaultImage" alt="" @error="onImgError" />
              <div class="slide-caption">
                <div class="slide-name">{{ item.name }}</div>
                <div class="slide-meta">热度 {{ Number(item.hot_score || 0).toFixed(1) }}</div>
              </div>
            </div>
          </el-carousel-item>
        </el-carousel>
      </el-card>

      <el-card class="headline-card" shadow="never">
        <template #header>
          <div class="headline-title">销量排行</div>
        </template>
        <el-skeleton v-if="headlineLoading" :rows="4" animated />
        <el-alert
          v-else-if="headlineError"
          :title="headlineError"
          type="error"
          :closable="false"
          show-icon
        />
        <el-empty v-else-if="topSales.length === 0" description="暂无排行" />
        <div v-else class="rank-list">
          <div
            v-for="(item, idx) in topSales"
            :key="item.id"
            class="rank-item"
            @click="goDetail(item.id)"
          >
            <span class="rank-no">{{ idx + 1 }}</span>
            <span class="rank-name">{{ item.name }}</span>
            <span class="rank-sales">销量 {{ item.sales }}</span>
          </div>
        </div>
      </el-card>
    </div>

    <div class="content">
      <aside class="sidebar">
        <el-card class="category-card" shadow="never">
          <template #header>
            <div class="category-header">分类</div>
          </template>
          <el-empty v-if="categories.length === 0" description="暂无分类" />
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
        <el-alert
          v-else-if="productError"
          :title="productError"
          type="error"
          :closable="false"
          show-icon
        />

        <el-empty v-else-if="products.length === 0" description="暂无商品" />

        <el-row :gutter="16">
          <el-col v-for="p in products" :key="p.id" :xs="24" :sm="12" :md="8" :lg="6">
            <el-card shadow="never" class="product-card" :body-style="{ padding: 0 }">
              <div class="img-wrap" @click="goDetail(p.id)">
                <img class="img" :src="getMainImage(p)" alt="" @error="onImgError" />
              </div>
              <div class="product-body">
                <div class="title" :title="p.name">{{ p.name }}</div>
                <div class="meta">
                  <span class="price">¥{{ p.price }}</span>
                  <span class="stock">库存：{{ p.stock }}</span>
                </div>
                <div class="actions">
                  <el-button size="small" @click="goDetail(p.id)">详情</el-button>
                  <el-button size="small" type="primary" @click="addToCart(p.id)">加入购物车</el-button>
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
import { onMounted, ref } from 'vue'
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
const topSales = ref([])
const hotFeed = ref([])
const headlineLoading = ref(false)
const headlineError = ref('')
const productError = ref('')
const defaultImage = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="100%" height="100%" fill="%23f2f3f5"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="%2390999f" font-size="24">No Image</text></svg>'

const onImgError = event => {
  if (!event?.target) return
  event.target.src = defaultImage
}

const loadCategories = async () => {
  try {
    const res = await productApi.getCategories()
    categories.value = res?.results || res || []
  } catch (e) {
    categories.value = []
    ElMessage.error(e?.response?.data?.error || '获取分类失败')
  }
}

const getMainImage = product => {
  const imgs = product?.images || []
  const main = imgs.find(i => i.is_main) || imgs[0]
  return main?.image_url || defaultImage
}

const loadHeadline = async () => {
  headlineLoading.value = true
  headlineError.value = ''
  try {
    const [rankRes, hotRes] = await Promise.all([
      productApi.getTopSales({ limit: 6 }),
      productApi.getHotFeed({ limit: 6 })
    ])
    topSales.value = rankRes
    hotFeed.value = hotRes
  } catch (e) {
    topSales.value = []
    hotFeed.value = []
    headlineError.value = e?.response?.data?.error || '获取榜单失败，请稍后重试'
    ElMessage.error(headlineError.value)
  } finally {
    headlineLoading.value = false
  }
}

const loadHot = async () => {
  loading.value = true
  productError.value = ''
  try {
    const res = await productApi.getHotProducts()
    products.value = res
  } catch (e) {
    products.value = []
    productError.value = e?.response?.data?.error || '获取商品失败，请稍后重试'
    ElMessage.error(productError.value)
  } finally {
    loading.value = false
  }
}

const loadByCategory = async categoryId => {
  loading.value = true
  productError.value = ''
  try {
    const res = await productApi.getProducts({ category: categoryId, status: true })
    products.value = res?.results || res || []
  } catch (e) {
    products.value = []
    productError.value = e?.response?.data?.error || '按分类获取商品失败'
    ElMessage.error(productError.value)
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
  productError.value = ''
  try {
    const res = await productApi.searchProducts(kw)
    products.value = res?.results || res || []
  } catch (e) {
    products.value = []
    productError.value = e?.response?.data?.error || '搜索商品失败'
    ElMessage.error(productError.value)
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
    if (e?.response?.status !== 401) {
      ElMessage.error(e?.response?.data?.error || '加入购物车失败')
    }
  }
}

const goDetail = id => {
  router.push(`/product/${id}`)
}

const goSeckillZone = () => {
  router.push('/seckill')
}

onMounted(async () => {
  await loadCategories()
  await Promise.all([loadHeadline(), loadHot()])
})
</script>

<style scoped>
.home {
  display: grid;
  gap: 16px;
}

.hero-panel {
  padding: 18px;
  border-radius: 16px;
  background: linear-gradient(120deg, #fff4ea, #eef7ff 56%, #f2fff8);
  border: 1px solid #e7edf5;
}

.hero-title {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: 0.3px;
  color: #23354d;
}

.hero-subtitle {
  margin-top: 6px;
  color: #5f6b7a;
  font-size: 13px;
}

.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 14px;
  flex-wrap: wrap;
}

.search {
  width: 460px;
  max-width: 100%;
}

.headline-grid {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(300px, 1fr);
  gap: 16px;
  align-items: start;
}

.headline-card {
  min-height: 0;
}

.headline-title {
  font-weight: 700;
  color: #23354d;
}

.slide {
  position: relative;
  width: 100%;
  height: 100%;
  cursor: pointer;
  overflow: hidden;
  border-radius: 12px;
  background: radial-gradient(circle at 20% 20%, #e5f0ff, #f6f8ff 50%, #fff7f0);
}

.slide-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  transition: transform 0.45s ease;
}

.slide:hover .slide-img {
  transform: scale(1.04);
}

.slide-caption {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 12px;
  color: #fff;
  background: linear-gradient(to top, rgba(16, 24, 40, 0.72), rgba(16, 24, 40, 0.08));
}

.slide-name {
  font-weight: 700;
}

.slide-meta {
  font-size: 12px;
  opacity: 0.94;
}

.rank-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rank-item {
  display: grid;
  grid-template-columns: 30px 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 10px;
  border: 1px solid #eaf0f8;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fbfdff;
}

.rank-item:hover {
  border-color: #cddcf1;
  transform: translateY(-1px);
}

.rank-no {
  color: #ff7b45;
  font-weight: 800;
  text-align: center;
}

.rank-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #22334b;
}

.rank-sales {
  color: #6c7a8d;
  font-size: 12px;
}

.content {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 16px;
}

.category-card {
  position: sticky;
  top: 88px;
}

.category-header {
  font-weight: 700;
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
  height: 190px;
  overflow: hidden;
  cursor: pointer;
  background: #f6f9ff;
}

.img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.35s ease;
}

.product-card:hover .img {
  transform: scale(1.04);
}

.product-body {
  padding: 12px;
}

.title {
  font-weight: 700;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #22334b;
}

.meta {
  display: flex;
  justify-content: space-between;
  color: #617081;
  font-size: 12px;
  margin-bottom: 10px;
}

.price {
  color: #ff5a45;
  font-weight: 700;
}

.actions {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.loading {
  padding: 20px;
  color: #667688;
}

@media (max-width: 1100px) {
  .headline-grid {
    grid-template-columns: 1fr;
  }

  .content {
    grid-template-columns: 1fr;
  }

  .category-card {
    position: static;
  }
}
</style>
