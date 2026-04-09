<template>
  <div class="orders-page">
    <el-card shadow="never">
      <template #header>
        <div class="header">
          我的订单
        </div>
      </template>

      <div class="filter-tabs">
        <el-radio-group v-model="activeTab" @change="handleTabChange">
          <el-radio-button value="">全部订单</el-radio-button>
          <el-radio-button value="pending">待支付</el-radio-button>
          <el-radio-button value="paid">已支付</el-radio-button>
        </el-radio-group>
      </div>

      <el-table :data="orders" style="width: 100%" v-loading="loading" empty-text="暂无订单">
        <el-table-column label="订单号" prop="order_id" width="240" />
        <el-table-column label="总价" width="120">
          <template #default="{ row }">
            ¥{{ row.total_price }}
          </template>
        </el-table-column>
        <el-table-column label="支付状态" width="130">
          <template #default="{ row }">
            <el-tag :type="paymentTagType(row.payment_status)">
              {{ row.payment_status_display || statusText(row.payment_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="物流状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.payment_status === 'paid'" :type="shippingTagType(row.shipping_status)">
              {{ row.shipping_status_display || shippingText(row.shipping_status) }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="收货地址" min-width="200">
          <template #default="{ row }">
            <div v-if="row.address_detail">
              {{ row.address_detail.province }}{{ row.address_detail.city }}{{ row.address_detail.district }}
              {{ row.address_detail.address }}
            </div>
            <div v-else>无</div>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.payment_status === 'pending'"
              size="small"
              type="primary"
              @click="openPayment(row)"
            >
              去支付
            </el-button>
            <el-button
              v-if="row.payment_status === 'pending'"
              size="small"
              type="danger"
              text
              @click="cancelOrder(row.id)"
            >
              取消
            </el-button>
            <el-button
              v-if="row.payment_status === 'paid'"
              size="small"
              type="info"
              text
              @click="viewDetail(row)"
            >
              查看详情
            </el-button>
            <el-button
              v-if="row.shipping_status === 'shipped' || row.shipping_status === 'in_transit' || row.shipping_status === 'arrived'"
              size="small"
              type="success"
              text
              @click="confirmReceive(row.id)"
            >
              确认收货
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <PaymentDialog
      v-model="paymentVisible"
      :order-id="currentOrder?.order_id"
      :amount="currentOrder?.total_price"
      @success="handlePaymentSuccess"
      @close="handlePaymentClose"
    />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { orderApi } from '../api/order'
import PaymentDialog from '../components/PaymentDialog.vue'

const router = useRouter()
const loading = ref(false)
const orders = ref([])
const paymentVisible = ref(false)
const currentOrder = ref(null)
const activeTab = ref('')

const load = async () => {
  loading.value = true
  try {
    const params = { page: 1 }
    if (activeTab.value) {
      params.payment_status = activeTab.value
    }
    const res = await orderApi.getOrders(params)
    orders.value = res?.results || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '获取订单失败')
  } finally {
    loading.value = false
  }
}

const handleTabChange = () => {
  load()
}

const openPayment = (row) => {
  currentOrder.value = row
  paymentVisible.value = true
}

const handlePaymentSuccess = () => {
  ElMessage.success('支付成功')
  load()
}

const handlePaymentClose = () => {
  currentOrder.value = null
}

const cancelOrder = async id => {
  try {
    await orderApi.cancelOrder(id)
    ElMessage.success('订单已取消')
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '取消失败')
  }
}

const confirmReceive = async id => {
  try {
    await orderApi.confirmDelivery(id)
    ElMessage.success('已确认收货')
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '确认失败')
  }
}

const viewDetail = (row) => {
  router.push(`/order/${row.id}`)
}

const statusText = status => {
  const map = {
    pending: '待支付',
    paid: '已支付'
  }
  return map[status] || status
}

const paymentTagType = status => {
  const map = {
    pending: 'warning',
    paid: 'success'
  }
  return map[status] || 'info'
}

const shippingText = status => {
  const map = {
    not_shipped: '未发货',
    shipped: '已发货',
    in_transit: '运输中',
    arrived: '已到达',
    signed: '已签收'
  }
  return map[status] || status
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

const formatTime = (time) => {
  if (!time) return ''
  return time.replace('T', ' ').slice(0, 19)
}

onMounted(load)
</script>

<style scoped>
.orders-page {
  padding: 18px;
}

.header {
  font-weight: 700;
}

.filter-tabs {
  margin-bottom: 16px;
}
</style>
