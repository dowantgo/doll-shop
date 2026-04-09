<template>
  <div class="product-detail">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="never">
          <div class="img-wrap">
            <img class="img" :src="mainImage" alt="" />
          </div>
          <div v-if="product?.images?.length" class="thumbs">
            <img
              v-for="img in product.images"
              :key="img.id"
              class="thumb"
              :src="img.image_url"
              :class="{ active: img.id === activeImageId }"
              @click="activeImageId = img.id"
            />
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="never">
          <div class="name">{{ product?.name }}</div>
          <div class="desc">{{ product?.description }}</div>

          <div class="price-row">
            <div class="price">￥{{ product?.price }}</div>
            <div class="stock">库存：{{ product?.stock }}</div>
          </div>

          <div class="buy-row">
            <el-input-number
              v-model="quantity"
              :min="1"
              :max="product?.stock || 1"
            />
            <el-button
              type="primary"
              :loading="loading"
              @click="addToCart"
            >
              加入购物车
            </el-button>
          </div>

          <el-divider />

          <div class="tips">
            <div>提示：商品是否为上架状态以接口返回为准。</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { productApi } from '../api/product'
import { cartApi } from '../api/cart'

const route = useRoute()
const router = useRouter()

const product = ref(null)
const loading = ref(false)
const quantity = ref(1)

const activeImageId = ref(null)

const mainImage = computed(() => {
  const imgs = product.value?.images || []
  if (!imgs.length) return ''
  const picked = imgs.find(i => i.id === activeImageId.value) || imgs.find(i => i.is_main) || imgs[0]
  return picked?.image_url || ''
})

const load = async () => {
  loading.value = true
  try {
    const id = route.params.id
    const res = await productApi.getProductDetail(id)
    product.value = res
    const imgs = res?.images || []
    const main = imgs.find(i => i.is_main) || imgs[0]
    activeImageId.value = main?.id || null
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '获取商品详情失败')
  } finally {
    loading.value = false
  }
}

const addToCart = async () => {
  if (!product.value?.id) return

  // Check if user is logged in
  const token = localStorage.getItem('token')
  if (!token) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }

  try {
    await cartApi.addToCart(product.value.id, quantity.value)
    ElMessage.success('已加入购物车')
    router.push('/cart')
  } catch (e) {
    // Error is handled by request interceptor (401 will redirect to login)
    if (e?.response?.status !== 401) {
      ElMessage.error(e?.response?.data?.error || '加入购物车失败')
    }
  }
}

onMounted(load)
</script>

<style scoped>
.product-detail {
  padding: 18px;
}

.img-wrap {
  height: 380px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafafa;
}

.img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.thumbs {
  display: flex;
  gap: 10px;
  padding-top: 10px;
  flex-wrap: wrap;
}

.thumb {
  width: 76px;
  height: 76px;
  object-fit: cover;
  border: 1px solid transparent;
  cursor: pointer;
}

.thumb.active {
  border-color: #409eff;
}

.name {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 10px;
}

.desc {
  color: #666;
  line-height: 1.6;
  margin-bottom: 16px;
}

.price-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 14px;
}

.price {
  color: #ff4d4f;
  font-size: 22px;
  font-weight: 700;
}

.stock {
  color: #666;
  font-size: 14px;
}

.buy-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.tips {
  color: #999;
  font-size: 12px;
}
</style>
