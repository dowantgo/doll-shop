<template>
  <div class="seckill-zone">
    <div class="zone-header">
      <div>
        <h2>秒杀商品专区</h2>
        <p class="zone-subtitle">同一活动可包含多个秒杀商品，库存有限，先到先得。</p>
        <div class="status-legend">
          <span class="legend-label">记录状态：</span>
          <el-tag
            v-for="item in reservationLegend"
            :key="item.value"
            size="small"
            :type="item.type"
            class="legend-tag"
          >
            {{ item.text }}
          </el-tag>
        </div>
      </div>
      <el-button @click="loadActivities" :loading="loading">刷新活动</el-button>
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="mb-16"
    />

    <el-skeleton v-if="loading" :rows="6" animated />
    <el-empty v-else-if="groups.length === 0" description="当前暂无秒杀活动" />

    <div v-else class="group-list">
      <el-card v-for="group in groups" :key="group.group_id" class="group-card" shadow="never">
        <template #header>
          <div class="group-head">
            <div>
              <div class="group-title">{{ group.name }}</div>
              <div class="group-meta">
                活动时间：{{ formatDate(group.start_at) }} ~ {{ formatDate(group.end_at) }}
              </div>
            </div>
            <div class="group-countdown-wrap">
              <el-tag
                v-if="group.status"
                size="small"
                :type="getActivityStatusType(group.status)"
                class="activity-status-tag"
              >
                {{ getActivityStatusText(group.status) }}
              </el-tag>
              <div class="group-countdown">结束倒计时：{{ getCountdownText(group.end_at) }}</div>
            </div>
          </div>
        </template>

        <el-row :gutter="16">
          <el-col v-for="item in group.items" :key="item.id" :xs="24" :sm="12" :md="8" :lg="6">
            <el-card class="seckill-card" shadow="hover" :body-style="{ padding: '0' }">
              <div class="img-wrap" @click="goDetail(item.product_id)">
                <img class="img" :src="item.main_image || defaultImage" alt="" @error="onImgError" />
                <span class="stock-tag">剩余 {{ item.remaining_stock }}</span>
              </div>

              <div class="card-body">
                <div class="title" :title="item.product_name">{{ item.product_name }}</div>
                <div class="price-line">
                  <span class="seckill-price">¥{{ item.seckill_price }}</span>
                  <span class="origin-price">总库存 {{ item.total_stock }}</span>
                </div>
                <div class="limit-line">每人限购 {{ item.per_user_limit || 1 }} 件</div>

                <div class="actions">
                  <el-button size="small" @click="goDetail(item.product_id)">查看商品</el-button>
                  <el-button
                    size="small"
                    type="danger"
                    :disabled="Number(item.remaining_stock || 0) <= 0"
                    @click="goDetail(item.product_id)"
                  >
                    立即抢购
                  </el-button>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { seckillApi } from '../api/seckill'

const router = useRouter()
const groups = ref([])
const loading = ref(false)
const error = ref('')
const nowTs = ref(Date.now())
const reservationLegend = [
  { value: 'reserved', text: seckillApi.formatReservationStatus('reserved'), type: seckillApi.formatReservationStatusType('reserved') },
  { value: 'ordered', text: seckillApi.formatReservationStatus('ordered'), type: seckillApi.formatReservationStatusType('ordered') },
  { value: 'paid', text: seckillApi.formatReservationStatus('paid'), type: seckillApi.formatReservationStatusType('paid') },
  { value: 'cancelled', text: seckillApi.formatReservationStatus('cancelled'), type: seckillApi.formatReservationStatusType('cancelled') },
  { value: 'expired', text: seckillApi.formatReservationStatus('expired'), type: seckillApi.formatReservationStatusType('expired') }
]
const defaultImage =
  'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="100%" height="100%" fill="%23f2f3f5"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="%2390999f" font-size="24">No Image</text></svg>'

const onImgError = event => {
  if (!event?.target) return
  event.target.src = defaultImage
}

let timer = null

const normalizeGroups = payload => {
  if (!Array.isArray(payload)) return []
  if (payload.length === 0) return []

  const first = payload[0]
  if (first && Array.isArray(first.items)) {
    return payload.map(group => ({
      group_id: group.group_id || `group-${group.name}-${group.start_at || ''}`,
      name: group.name || '秒杀活动',
      start_at: group.start_at,
      end_at: group.end_at,
      status: group.status,
      items: Array.isArray(group.items) ? group.items : []
    }))
  }

  return payload.map(item => ({
    group_id: item.group_id || `activity-${item.id}`,
    name: item.name || '秒杀活动',
    start_at: item.start_at,
    end_at: item.end_at,
    status: item.status,
    items: [item]
  }))
}

const startTicker = () => {
  if (timer) return
  timer = setInterval(() => {
    nowTs.value = Date.now()
  }, 1000)
}

const stopTicker = () => {
  if (!timer) return
  clearInterval(timer)
  timer = null
}

const getCountdownText = endAt => {
  if (!endAt) return '--'
  const endMs = new Date(endAt).getTime()
  if (Number.isNaN(endMs)) return '--'

  const diff = endMs - nowTs.value
  if (diff <= 0) return '已结束'

  const totalSec = Math.floor(diff / 1000)
  const h = String(Math.floor(totalSec / 3600)).padStart(2, '0')
  const m = String(Math.floor((totalSec % 3600) / 60)).padStart(2, '0')
  const s = String(totalSec % 60).padStart(2, '0')
  return `${h}:${m}:${s}`
}

const formatDate = value => {
  if (!value) return '--'
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return value
  const y = dt.getFullYear()
  const m = String(dt.getMonth() + 1).padStart(2, '0')
  const d = String(dt.getDate()).padStart(2, '0')
  const hh = String(dt.getHours()).padStart(2, '0')
  const mm = String(dt.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}`
}

const getActivityStatusText = status => seckillApi.formatActivityStatus(status)
const getActivityStatusType = status => seckillApi.formatActivityStatusType(status)

const loadActivities = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await seckillApi.listActivities()
    groups.value = normalizeGroups(res)
  } catch (e) {
    groups.value = []
    error.value = seckillApi.normalizeSeckillError(e, '加载秒杀活动失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

const goDetail = productId => {
  router.push(`/product/${productId}`)
}

onMounted(async () => {
  startTicker()
  await loadActivities()
})

onBeforeUnmount(() => {
  stopTicker()
})
</script>

<style scoped>
.seckill-zone {
  padding: 8px;
  display: grid;
  gap: 14px;
}

.zone-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 14px;
  border: 1px solid #e5edf7;
  background: linear-gradient(120deg, #fff5eb, #eef7ff 62%, #f3fff9);
}

.zone-header h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 800;
  color: #23354d;
}

.zone-subtitle {
  margin: 6px 0 0;
  color: #5f6b7a;
  font-size: 13px;
}

.status-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}

.legend-label {
  color: #6b788a;
  font-size: 12px;
}

.legend-tag {
  margin-right: 0;
}

.mb-16 {
  margin-bottom: 16px;
}

.group-list {
  display: grid;
  gap: 16px;
}

.group-card {
  border: 1px solid #e6edf7;
  border-radius: 14px;
  overflow: hidden;
}

.group-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.group-countdown-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.group-title {
  font-size: 19px;
  font-weight: 800;
  color: #23354d;
}

.group-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #6b788a;
}

.group-countdown {
  font-size: 13px;
  color: #cc6f00;
  font-weight: 700;
  padding: 6px 10px;
  border-radius: 999px;
  background: #fff4e6;
  border: 1px solid #ffe0b3;
}

.activity-status-tag {
  align-self: flex-end;
}

.seckill-card {
  margin-bottom: 12px;
  border: 1px solid #e9eff8;
  border-radius: 12px;
  overflow: hidden;
}

.img-wrap {
  position: relative;
  height: 192px;
  background: radial-gradient(circle at 15% 20%, #e9f3ff, #f7f9ff 58%, #fff8f3);
  cursor: pointer;
  overflow: hidden;
}

.img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  transition: transform 0.35s ease;
}

.seckill-card:hover .img {
  transform: scale(1.04);
}

.stock-tag {
  position: absolute;
  right: 10px;
  top: 10px;
  padding: 3px 10px;
  font-size: 12px;
  color: #fff;
  background: linear-gradient(135deg, rgba(245, 108, 108, 0.95), rgba(255, 128, 97, 0.9));
  border-radius: 999px;
}

.card-body {
  padding: 12px;
}

.title {
  font-weight: 800;
  font-size: 15px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #23354d;
}

.price-line {
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.seckill-price {
  color: #f45d43;
  font-size: 24px;
  font-weight: 800;
}

.origin-price {
  color: #748397;
  font-size: 12px;
}

.limit-line {
  margin-top: 6px;
  color: #526074;
  font-size: 12px;
  background: #f4f8ff;
  padding: 4px 8px;
  border-radius: 8px;
  display: inline-block;
}

.actions {
  margin-top: 12px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

@media (max-width: 992px) {
  .seckill-zone {
    padding: 0;
  }

  .group-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .zone-header {
    padding: 12px;
  }

  .zone-header h2 {
    font-size: 22px;
  }
}
</style>
