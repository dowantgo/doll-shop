<template>
  <div class="product-detail" v-loading="loading">
    <el-alert
      v-if="productError"
      :title="productError"
      type="error"
      :closable="false"
      show-icon
      class="mb-16"
    />
    <el-empty v-if="!loading && !product" description="商品不存在或已下架" />

    <el-row v-if="product" :gutter="20">
      <el-col :xs="24" :md="12">
        <el-card shadow="never">
          <div class="img-wrap">
            <img class="img" :src="mainImage" alt="" @error="onImgError" />
          </div>
          <div v-if="product?.images?.length" class="thumbs">
            <img
              v-for="img in product.images"
              :key="img.id"
              class="thumb"
              :src="img.image_url"
              :class="{ active: img.id === activeImageId }"
              @error="onImgError"
              @click="activeImageId = img.id"
            />
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="12">
        <el-card shadow="never">
          <div class="name">{{ product?.name }}</div>
          <div class="desc">{{ product?.description }}</div>

          <div class="price-row">
            <div class="price">¥{{ product?.price }}</div>
            <div class="stock">库存：{{ product?.stock }}</div>
          </div>

          <div v-if="activeSeckill" class="seckill-panel">
            <div class="seckill-line">
              <span class="seckill-label">秒杀价</span>
              <span class="seckill-price">¥{{ activeSeckill.seckill_price }}</span>
              <span class="seckill-stock">剩余 {{ activeSeckill.remaining_stock }}</span>
              <span class="seckill-limit">每人限购 {{ activeSeckill.per_user_limit || 1 }} 件</span>
              <el-tag size="small" :type="seckillStatusType">{{ seckillStatusText }}</el-tag>
            </div>
            <el-button
              type="danger"
              size="small"
              :disabled="Number(activeSeckill.remaining_stock || 0) <= 0"
              @click="openSeckillDialog"
            >
              立即秒杀
            </el-button>
          </div>
          <div v-if="seckillInlineError" class="seckill-inline-error">{{ seckillInlineError }}</div>
          <el-alert
            v-else-if="seckillError"
            :title="seckillError"
            type="warning"
            :closable="false"
            show-icon
            class="mb-12"
          />

          <div class="buy-row">
            <el-input-number v-model="quantity" :min="1" :max="product?.stock || 1" />
            <el-button type="primary" :loading="loading" @click="addToCart">加入购物车</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card v-if="product" class="review-card" shadow="never">
      <template #header>
        <div class="review-title">商品评价</div>
      </template>

      <div class="review-form">
        <el-rate v-model="reviewForm.rating" :max="5" show-score />
        <el-input
          v-model="reviewForm.content"
          type="textarea"
          :rows="3"
          maxlength="1000"
          show-word-limit
          placeholder="分享你的购买体验..."
        />
        <div class="review-form-actions">
          <el-button type="primary" :loading="reviewSubmitting" @click="submitReview">提交评价</el-button>
          <span class="review-tip">仅已购买用户可评价，发布后会立即展示</span>
        </div>
        <el-alert
          v-if="reviewSubmissionFeedback"
          :title="reviewSubmissionFeedback.title"
          :type="reviewSubmissionFeedback.type"
          :closable="true"
          show-icon
          class="review-feedback"
          @close="reviewSubmissionFeedback = null"
        >
          <div class="feedback-body">
            <div v-if="reviewSubmissionFeedback.hitSensitiveWords.length" class="feedback-line">
              命中的敏感词：
              <el-tag
                v-for="word in reviewSubmissionFeedback.hitSensitiveWords"
                :key="word"
                size="small"
                type="warning"
                class="feedback-tag"
              >
                {{ word }}
              </el-tag>
            </div>
            <div v-if="reviewSubmissionFeedback.sanitizedContent" class="feedback-line">
              处理后的内容：<span class="feedback-content">{{ reviewSubmissionFeedback.sanitizedContent }}</span>
            </div>
            <div v-if="reviewSubmissionFeedback.suggestion" class="feedback-line">
              建议：{{ reviewSubmissionFeedback.suggestion }}
            </div>
          </div>
        </el-alert>
      </div>

      <el-divider />

      <div v-loading="reviewLoading">
        <el-alert
          v-if="reviewError"
          :title="reviewError"
          type="error"
          :closable="false"
          show-icon
          class="mb-12"
        />
        <el-empty v-if="reviews.length === 0" description="暂无已通过评价" />
        <div v-else class="review-list">
          <div v-for="item in reviews" :key="item.id" class="review-item">
            <div class="review-user">{{ item.user_name || `用户${item.user_id}` }}</div>
            <el-rate :model-value="item.rating" disabled size="small" />
            <div class="review-content">{{ item.content }}</div>
            <div class="review-time">{{ formatDate(item.created_at) }}</div>
            <div v-if="item.replies?.length" class="reply-list">
              <div v-for="reply in item.replies" :key="reply.id" class="reply-item">
                <span class="reply-user">{{ reply.user_name || `用户${reply.user_id}` }}：</span>
                <span class="reply-content">{{ reply.content }}</span>
                <span class="reply-time">{{ formatDate(reply.created_at) }}</span>
              </div>
            </div>
            <div class="reply-actions">
              <el-button link type="primary" @click="toggleReply(item.id)">
                {{ replyOpen[item.id] ? '取消回复' : '回复' }}
              </el-button>
            </div>
            <div v-if="replyOpen[item.id]" class="reply-form">
              <el-input
                v-model="replyDraft[item.id]"
                type="textarea"
                :rows="2"
                maxlength="1000"
                show-word-limit
                placeholder="写下你的回复..."
              />
              <div class="reply-form-actions">
                <el-button
                  type="primary"
                  size="small"
                  :loading="replySubmitting[item.id]"
                  @click="submitReply(item.id)"
                >
                  发送回复
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="seckillDialogVisible" title="秒杀下单" width="520px">
      <div v-if="seckillAddresses.length === 0">
        <el-alert
          title="你还没有收货地址，请先在个人中心新增地址。"
          type="warning"
          :closable="false"
          show-icon
        />
        <div class="reply-form-actions">
          <el-button type="primary" @click="goAccountAddress">去添加地址</el-button>
        </div>
      </div>
      <div v-else class="seckill-dialog-body">
        <el-form label-width="90px">
          <el-form-item label="收货地址">
            <el-select v-model="seckillAddressId" placeholder="请选择地址" style="width: 100%">
              <el-option
                v-for="addr in seckillAddresses"
                :key="addr.id"
                :label="`${addr.name} ${addr.phone} ${addr.province}${addr.city}${addr.district} ${addr.address}`"
                :value="addr.id"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="seckillDialogVisible = false">取消</el-button>
        <el-button
          type="danger"
          :disabled="seckillAddresses.length === 0"
          :loading="seckillSubmitting"
          @click="submitSeckillOrder"
        >
          提交秒杀订单
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { cartApi } from '../api/cart'
import { productApi } from '../api/product'
import { reviewApi } from '../api/review'
import { seckillApi } from '../api/seckill'
import { userApi } from '../api/user'

const route = useRoute()
const router = useRouter()

const product = ref(null)
const loading = ref(false)
const quantity = ref(1)
const activeImageId = ref(null)

const reviewLoading = ref(false)
const reviewSubmitting = ref(false)
const reviews = ref([])
const productError = ref('')
const reviewError = ref('')
const reviewSubmissionFeedback = ref(null)
const reviewForm = ref({
  rating: 5,
  content: ''
})
const replyDraft = ref({})
const replyOpen = ref({})
const replySubmitting = ref({})
const activeSeckill = ref(null)
const seckillError = ref('')
const seckillDialogVisible = ref(false)
const seckillAddresses = ref([])
const seckillAddressId = ref(null)
const seckillSubmitting = ref(false)
const seckillInlineError = ref('')
const defaultImage = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="100%" height="100%" fill="%23f2f3f5"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="%2390999f" font-size="24">No Image</text></svg>'

const onImgError = event => {
  if (!event?.target) return
  event.target.src = defaultImage
}

const mainImage = computed(() => {
  const imgs = product.value?.images || []
  if (!imgs.length) return ''
  const picked = imgs.find(i => i.id === activeImageId.value) || imgs.find(i => i.is_main) || imgs[0]
  return picked?.image_url || ''
})

const loadProduct = async () => {
  loading.value = true
  productError.value = ''
  try {
    const id = route.params.id
    const res = await productApi.getProductDetail(id)
    product.value = res
    const imgs = res?.images || []
    const main = imgs.find(i => i.is_main) || imgs[0]
    activeImageId.value = main?.id || null
  } catch (e) {
    product.value = null
    productError.value = e?.response?.data?.error || '获取商品详情失败'
    ElMessage.error(productError.value)
  } finally {
    loading.value = false
  }
}

const loadSeckillActivity = async () => {
  seckillError.value = ''
  try {
    const id = route.params.id
    const res = await seckillApi.getProductActiveActivity(id)
    activeSeckill.value = res
  } catch (e) {
    activeSeckill.value = null
    if (e?.response?.status && e.response.status !== 404) {
      seckillError.value = e?.response?.data?.error || '秒杀活动加载失败'
    }
  }
}

const loadReviews = async () => {
  reviewLoading.value = true
  reviewError.value = ''
  try {
    const id = route.params.id
    const res = await reviewApi.getProductReviews(id, { page: 1, page_size: 10 })
    reviews.value = res.results
    replyOpen.value = {}
    replyDraft.value = {}
    replySubmitting.value = {}
  } catch (e) {
    reviews.value = []
    replyOpen.value = {}
    replyDraft.value = {}
    replySubmitting.value = {}
    reviewError.value = e?.response?.data?.error || '获取评价失败，请稍后重试'
    ElMessage.error(reviewError.value)
  } finally {
    reviewLoading.value = false
  }
}

const submitReview = async () => {
  const token = localStorage.getItem('token')
  if (!token) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }

  if (!reviewForm.value.content.trim()) {
    ElMessage.warning('请输入评价内容')
    return
  }

  reviewSubmitting.value = true
  try {
    const res = await reviewApi.createProductReview(route.params.id, {
      rating: reviewForm.value.rating,
      content: reviewForm.value.content.trim()
    })
    const feedback = reviewApi.extractSubmissionFeedback(res)
    reviewSubmissionFeedback.value = {
      type: feedback.hitSensitiveWords.length ? 'warning' : 'success',
      title: feedback.hitSensitiveWords.length ? '评价已发布，部分内容已做敏感词处理' : '评价发布成功',
      ...feedback
    }
    ElMessage.success('评价发布成功')
    reviewForm.value.content = ''
    reviewForm.value.rating = 5
    await loadReviews()
  } catch (e) {
    reviewSubmissionFeedback.value = null
    ElMessage.error(e?.response?.data?.error || e?.response?.data?.message || '评价提交失败')
  } finally {
    reviewSubmitting.value = false
  }
}

const toggleReply = reviewId => {
  const opened = !!replyOpen.value[reviewId]
  replyOpen.value[reviewId] = !opened
  if (!opened && typeof replyDraft.value[reviewId] !== 'string') {
    replyDraft.value[reviewId] = ''
  }
}

const submitReply = async reviewId => {
  const token = localStorage.getItem('token')
  if (!token) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }

  const content = (replyDraft.value[reviewId] || '').trim()
  if (!content) {
    ElMessage.warning('请输入回复内容')
    return
  }

  replySubmitting.value[reviewId] = true
  try {
    await reviewApi.createReviewReply(reviewId, { content })
    ElMessage.success('回复发送成功')
    replyDraft.value[reviewId] = ''
    replyOpen.value[reviewId] = false
    await loadReviews()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '回复发送失败')
  } finally {
    replySubmitting.value[reviewId] = false
  }
}

const goAccountAddress = () => {
  seckillDialogVisible.value = false
  router.push('/account')
}

const openSeckillDialog = async () => {
  const token = localStorage.getItem('token')
  if (!token) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }

  seckillInlineError.value = ''
  try {
    const res = await userApi.getAddresses()
    const list = res?.results || res || []
    seckillAddresses.value = list
    const def = list.find(item => item.is_default) || list[0] || null
    seckillAddressId.value = def?.id || null
    seckillDialogVisible.value = true
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '获取地址失败')
  }
}

const seckillStatusText = computed(() => seckillApi.formatActivityStatus(activeSeckill.value?.status))
const seckillStatusType = computed(() => seckillApi.formatActivityStatusType(activeSeckill.value?.status))

const submitSeckillOrder = async () => {
  seckillInlineError.value = ''
  if (!activeSeckill.value?.id) {
    ElMessage.error('当前商品没有可用秒杀活动')
    return
  }
  if (!seckillAddressId.value) {
    ElMessage.warning('请选择收货地址')
    return
  }

  seckillSubmitting.value = true
  const idempotencyKey = `sk-${activeSeckill.value.id}-${Date.now()}`
  try {
    const reserveRes = await seckillApi.preReserve(
      {
        activity_id: activeSeckill.value.id,
        quantity: 1
      },
      idempotencyKey
    )
    const reservationId = reserveRes?.data?.id
    if (!reservationId) {
      throw new Error('Reservation id missing')
    }
    await seckillApi.createOrder({
      reservation_id: reservationId,
      address_id: seckillAddressId.value
    })

    ElMessage.success('秒杀订单已创建，请前往订单页支付')
    seckillDialogVisible.value = false
    await Promise.all([loadProduct(), loadSeckillActivity()])
    router.push('/orders')
  } catch (e) {
    const msg = seckillApi.normalizeSeckillError(e, '秒杀下单失败')
    seckillInlineError.value = msg
    ElMessage.error(msg)
  } finally {
    seckillSubmitting.value = false
  }
}

const addToCart = async () => {
  if (!product.value?.id) return

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
    if (e?.response?.status !== 401) {
      ElMessage.error(e?.response?.data?.error || '加入购物车失败')
    }
  }
}

const formatDate = value => {
  if (!value) return '-'
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return value
  const y = dt.getFullYear()
  const m = String(dt.getMonth() + 1).padStart(2, '0')
  const d = String(dt.getDate()).padStart(2, '0')
  const hh = String(dt.getHours()).padStart(2, '0')
  const mm = String(dt.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}`
}

onMounted(async () => {
  await Promise.all([loadProduct(), loadReviews(), loadSeckillActivity()])
})

watch(
  () => route.params.id,
  async () => {
    quantity.value = 1
    seckillDialogVisible.value = false
    seckillInlineError.value = ''
    seckillAddresses.value = []
    seckillAddressId.value = null
    reviewSubmissionFeedback.value = null
    await Promise.all([loadProduct(), loadReviews(), loadSeckillActivity()])
  }
)
</script>

<style scoped>
.product-detail {
  padding: 8px;
}

.mb-16 {
  margin-bottom: 16px;
}

.mb-12 {
  margin-bottom: 12px;
}

.img-wrap {
  height: 440px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 20% 20%, #f2f7ff, #f9fbff 62%, #fff8f2);
  border-radius: 12px;
}

.img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
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
  border: 2px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.thumb.active {
  border-color: #2d8cff;
  transform: translateY(-1px);
}

.name {
  font-size: 24px;
  font-weight: 800;
  margin-bottom: 10px;
  color: #23354d;
}

.desc {
  color: #596679;
  line-height: 1.7;
  margin-bottom: 16px;
}

.price-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 14px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f8fbff;
}

.price {
  color: #ff6145;
  font-size: 28px;
  font-weight: 800;
}

.stock {
  color: #627286;
  font-size: 14px;
}

.buy-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 8px;
}

.seckill-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  margin-bottom: 12px;
  border-radius: 10px;
  background: linear-gradient(135deg, #fff2ec, #fff7f4);
  border: 1px solid #ffd2c2;
}

.seckill-line {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #606266;
  flex-wrap: wrap;
}

.seckill-label {
  font-size: 12px;
  color: #8c98ab;
}

.seckill-price {
  font-size: 22px;
  font-weight: 800;
  color: #f2573c;
}

.seckill-stock {
  font-size: 12px;
  color: #d48806;
}

.seckill-limit {
  font-size: 12px;
  color: #6d7a8d;
}

.seckill-inline-error {
  margin-bottom: 12px;
  font-size: 13px;
  color: #f56c6c;
}

.review-card {
  margin-top: 18px;
}

.review-title {
  font-weight: 700;
  color: #243a56;
}

.review-form {
  display: grid;
  gap: 12px;
}

.review-form-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.review-feedback {
  margin-top: 4px;
}

.feedback-body {
  display: grid;
  gap: 8px;
}

.feedback-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  color: #5e6b7b;
  line-height: 1.6;
}

.feedback-tag {
  margin-right: 4px;
}

.feedback-content {
  color: #23354d;
  font-weight: 600;
}

.review-tip {
  color: #8b97a9;
  font-size: 12px;
}

.review-list {
  display: grid;
  gap: 12px;
}

.review-item {
  border: 1px solid #e7edf6;
  border-radius: 10px;
  padding: 12px;
  display: grid;
  gap: 8px;
  background: #fbfdff;
}

.review-user {
  font-weight: 700;
  color: #23354d;
}

.review-content {
  color: #2b3a4f;
  line-height: 1.7;
}

.review-time {
  color: #8b97a9;
  font-size: 12px;
}

.reply-list {
  display: grid;
  gap: 6px;
  margin-top: 6px;
  padding-top: 8px;
  border-top: 1px dashed #d8e3f0;
}

.reply-item {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 13px;
  color: #56657a;
}

.reply-user {
  font-weight: 700;
}

.reply-content {
  color: #2d3a4a;
}

.reply-time {
  color: #8a96a8;
}

.reply-actions {
  margin-top: 4px;
}

.reply-form {
  display: grid;
  gap: 8px;
  margin-top: 6px;
}

.reply-form-actions {
  display: flex;
  justify-content: flex-end;
}

.seckill-dialog-body {
  padding-top: 6px;
}

@media (max-width: 992px) {
  .product-detail {
    padding: 0;
  }

  .img-wrap {
    height: 320px;
  }

  .name {
    font-size: 20px;
  }

  .price {
    font-size: 24px;
  }

  .buy-row {
    flex-wrap: wrap;
  }

  .seckill-panel {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
