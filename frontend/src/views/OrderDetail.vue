<template>
  <div class="order-detail-page">
    <el-card shadow="never" v-loading="loading" class="detail-card">
      <template #header>
        <div class="header">
          <el-button text @click="router.back()">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <span class="title">订单详情</span>
        </div>
      </template>

      <div v-if="order" class="order-content">
        <div class="order-info">
          <h3>订单信息</h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="订单号">{{ order.order_id }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatTime(order.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="支付状态">
              <el-tag :type="paymentTagType(order.payment_status)">
                {{ order.payment_status_display }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="支付方式">{{ order.payment_method_display || '-' }}</el-descriptions-item>
            <el-descriptions-item label="订单总价">
              <span class="price">¥{{ order.total_price }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="支付时间">
              {{ order.paid_at ? formatTime(order.paid_at) : '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="shipping-info" v-if="order.payment_status === 'paid'">
          <h3>物流信息</h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="快递公司">{{ order.shipping_company_display || '-' }}</el-descriptions-item>
            <el-descriptions-item label="物流状态">
              <el-tag :type="shippingTagType(order.shipping_status)">
                {{ order.shipping_status_display }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="快递单号">{{ order.tracking_no || '-' }}</el-descriptions-item>
            <el-descriptions-item label="发货时间">
              {{ order.shipped_at ? formatTime(order.shipped_at) : '-' }}
            </el-descriptions-item>
          </el-descriptions>
          <div class="logistics-panel">
            <div class="logistics-head">
              <span>物流轨迹</span>
              <el-button size="small" @click="loadLogistics" :loading="logisticsLoading">刷新轨迹</el-button>
            </div>
            <el-alert
              v-if="logisticsMessage"
              :title="logisticsMessage"
              :type="logisticsData.available ? 'success' : 'warning'"
              :closable="false"
              show-icon
            />
            <el-timeline v-if="logisticsData.traces?.length" class="timeline">
              <el-timeline-item
                v-for="(trace, idx) in logisticsData.traces"
                :key="idx"
                :timestamp="trace.time || '-'"
                :type="idx === 0 ? 'primary' : ''"
              >
                <div class="trace-status">{{ trace.status || '-' }}</div>
                <div class="trace-desc">{{ trace.description || '-' }}</div>
                <div class="trace-loc" v-if="trace.location">{{ trace.location }}</div>
              </el-timeline-item>
            </el-timeline>
          </div>
        </div>

        <div class="address-info">
          <h3>收货地址</h3>
          <el-descriptions :column="1" border v-if="order.address_detail">
            <el-descriptions-item label="收货人">
              {{ order.address_detail.name }} {{ order.address_detail.phone }}
            </el-descriptions-item>
            <el-descriptions-item label="详细地址">
              {{ order.address_detail.province }}{{ order.address_detail.city }}{{ order.address_detail.district }}{{ order.address_detail.address }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="items-info">
          <h3>商品明细</h3>
          <el-table :data="order.items" border>
            <el-table-column label="商品图片" width="100">
              <template #default="{ row }">
                <el-image
                  :src="row.product_image"
                  :preview-src-list="[row.product_image]"
                  fit="cover"
                  style="width: 60px; height: 60px"
                />
              </template>
            </el-table-column>
            <el-table-column label="商品名称" prop="product_name" min-width="200" />
            <el-table-column label="单价" width="120">
              <template #default="{ row }">¥{{ row.price }}</template>
            </el-table-column>
            <el-table-column label="数量" prop="quantity" width="100" />
            <el-table-column label="小计" width="120">
              <template #default="{ row }"><span class="price">¥{{ row.subtotal }}</span></template>
            </el-table-column>
            <el-table-column label="退款" width="180" v-if="order.payment_status === 'paid'">
              <template #default="{ row }">
                <el-button size="small" type="warning" text @click="openRefundDialog(row)">申请退款</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="refunds-info" v-if="order.payment_status === 'paid'">
          <h3>退款记录</h3>
          <el-empty v-if="refunds.length === 0" description="暂无退款记录" />
          <el-table v-else :data="refunds" border>
            <el-table-column prop="refund_no" label="退款单号" min-width="200" />
            <el-table-column prop="product_name" label="商品" min-width="150" />
            <el-table-column prop="quantity" label="数量" width="80" />
            <el-table-column prop="requested_amount" label="申请金额" width="120" />
            <el-table-column prop="approved_amount" label="审核金额" width="120" />
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="refundStatusType(row.status)">{{ refundStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="review_note" label="审核备注" min-width="180" />
          </el-table>
        </div>

        <div class="actions">
          <el-button
            v-if="order.shipping_status === 'shipped' || order.shipping_status === 'in_transit' || order.shipping_status === 'arrived'"
            type="success"
            @click="confirmReceive"
          >
            确认收货
          </el-button>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="refundDialogVisible" title="申请部分退款" width="460px">
      <el-form :model="refundForm" label-width="100px">
        <el-form-item label="商品">
          <span>{{ refundForm.product_name || '-' }}</span>
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="refundForm.quantity" :min="1" :max="refundForm.max_quantity || 1" />
        </el-form-item>
        <el-form-item label="原因">
          <el-input v-model="refundForm.reason" type="textarea" :rows="3" maxlength="255" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="refundDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="refundSubmitting" @click="submitRefund">提交申请</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { orderApi } from '../api/order'
import { refundApi } from '../api/refund'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const order = ref(null)
const logisticsData = ref({ available: false, traces: [] })
const logisticsLoading = ref(false)
const logisticsMessage = ref('')
const refunds = ref([])
const refundDialogVisible = ref(false)
const refundSubmitting = ref(false)
const refundForm = ref({
  order_item_id: null,
  product_name: '',
  quantity: 1,
  max_quantity: 1,
  reason: ''
})

const load = async () => {
  loading.value = true
  try {
    const res = await orderApi.getOrderDetail(route.params.id)
    order.value = res
    if (order.value?.payment_status === 'paid') {
      await Promise.all([loadLogistics(), loadRefunds()])
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '获取订单详情失败')
    router.back()
  } finally {
    loading.value = false
  }
}

const loadLogistics = async () => {
  if (!order.value) return
  logisticsLoading.value = true
  try {
    const res = await orderApi.getLogistics(order.value.id)
    logisticsData.value = res || { available: false, traces: [] }
    logisticsMessage.value = res?.message || ''
  } catch (e) {
    logisticsData.value = { available: false, traces: [] }
    logisticsMessage.value = e?.response?.data?.error || '暂无法获取轨迹'
  } finally {
    logisticsLoading.value = false
  }
}

const loadRefunds = async () => {
  if (!order.value) return
  try {
    const res = await refundApi.getMyRefunds({ order_id: order.value.order_id })
    refunds.value = res?.results || res || []
  } catch (e) {
    refunds.value = []
  }
}

const openRefundDialog = row => {
  refundForm.value = {
    order_item_id: row.id,
    product_name: row.product_name,
    quantity: 1,
    max_quantity: Number(row.quantity) || 1,
    reason: ''
  }
  refundDialogVisible.value = true
}

const submitRefund = async () => {
  if (!order.value) return
  refundSubmitting.value = true
  try {
    await refundApi.createRefund({
      order_id: order.value.order_id,
      order_item_id: refundForm.value.order_item_id,
      quantity: refundForm.value.quantity,
      reason: refundForm.value.reason || ''
    })
    ElMessage.success('退款申请已提交')
    refundDialogVisible.value = false
    await loadRefunds()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '提交退款失败')
  } finally {
    refundSubmitting.value = false
  }
}

const confirmReceive = async () => {
  try {
    await ElMessageBox.confirm('确认已收到货物吗？', '确认收货', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'info'
    })
    await orderApi.confirmDelivery(order.value.id)
    ElMessage.success('已确认收货')
    await load()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.error || '确认失败')
    }
  }
}

const paymentTagType = status => {
  const map = {
    pending: 'warning',
    paid: 'success'
  }
  return map[status] || 'info'
}

const shippingTagType = status => {
  const map = {
    not_shipped: 'info',
    shipped: 'warning',
    in_transit: 'primary',
    arrived: 'success',
    signed: 'success'
  }
  return map[status] || 'info'
}

const formatTime = time => {
  if (!time) return ''
  return time.replace('T', ' ').slice(0, 19)
}

const refundStatusText = status => {
  const map = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝',
    refunding: '退款中',
    success: '退款成功',
    failed: '退款失败'
  }
  return map[status] || status
}

const refundStatusType = status => {
  const map = {
    pending: 'warning',
    approved: 'primary',
    rejected: 'danger',
    refunding: 'info',
    success: 'success',
    failed: 'danger'
  }
  return map[status] || 'info'
}

onMounted(load)
</script>

<style scoped>
.order-detail-page {
  padding: 8px;
}

.detail-card {
  border-radius: 14px;
}

.header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.title {
  font-weight: 800;
  font-size: 18px;
  color: #23354d;
}

.order-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.order-info h3,
.shipping-info h3,
.address-info h3,
.items-info h3 {
  margin-bottom: 12px;
  font-size: 16px;
  color: #2c3e54;
}

.price {
  color: #f56c6c;
  font-weight: 700;
}

.actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
  border-top: 1px solid #e6edf6;
}

.logistics-panel {
  margin-top: 12px;
}

.logistics-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.timeline {
  margin-top: 10px;
}

.trace-status {
  font-weight: 700;
  color: #23354d;
}

.trace-desc {
  margin-top: 4px;
  color: #54667d;
}

.trace-loc {
  margin-top: 4px;
  color: #8090a6;
  font-size: 12px;
}
</style>
