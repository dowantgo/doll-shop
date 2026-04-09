<template>
  <div class="order-manage">
    <div class="page-header">
      <h1>订单管理</h1>
    </div>

    <el-card shadow="never">
      <el-table :data="orders" v-loading="loading" style="width: 100%">
        <el-table-column prop="order_id" label="订单号" width="220" />
        <el-table-column prop="user_name" label="用户" width="100" />
        <el-table-column prop="total_price" label="金额" width="100">
          <template #default="{ row }">¥{{ row.total_price }}</template>
        </el-table-column>
        <el-table-column label="支付状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getPaymentStatusType(row.payment_status)">
              {{ row.payment_status_display || getPaymentStatusText(row.payment_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="物流状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getShippingStatusType(row.shipping_status)">
              {{ row.shipping_status_display || getShippingStatusText(row.shipping_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="shipping_company_display" label="快递公司" width="100">
          <template #default="{ row }">{{ row.shipping_company_display || '-' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.payment_status === 'paid'" type="primary" size="small" @click="handleShip(row)">发货</el-button>
            <el-button v-if="row.payment_status === 'paid'" type="info" size="small" @click="openShippingDialog(row)">物流</el-button>
            <el-button type="info" size="small" text @click="handleView(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="shippingDialogVisible" title="编辑物流信息" width="500px">
      <el-form :model="shippingForm" label-width="100px">
        <el-form-item label="快递公司">
          <el-select v-model="shippingForm.shipping_company" placeholder="请选择快递公司" style="width: 100%">
            <el-option label="顺丰速运" value="sf" />
            <el-option label="中通快递" value="zto" />
            <el-option label="圆通速递" value="yto" />
            <el-option label="申通快递" value="sto" />
            <el-option label="韵达速递" value="yunda" />
          </el-select>
        </el-form-item>
        <el-form-item label="物流状态">
          <el-select v-model="shippingForm.shipping_status" placeholder="请选择物流状态" style="width: 100%">
            <el-option label="未发货" value="not_shipped" />
            <el-option label="已发货" value="shipped" />
            <el-option label="运输中" value="in_transit" />
            <el-option label="已到达" value="arrived" />
            <el-option label="已签收" value="signed" />
          </el-select>
        </el-form-item>
        <el-form-item label="快递单号">
          <el-input v-model="shippingForm.tracking_no" placeholder="请输入快递单号" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="shippingDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveShipping" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailDialogVisible" title="订单详情" width="800px">
      <div v-if="currentOrder" class="order-detail">
        <el-descriptions title="订单信息" :column="2" border>
          <el-descriptions-item label="订单号">{{ currentOrder.order_id }}</el-descriptions-item>
          <el-descriptions-item label="用户">{{ currentOrder.user_name }}</el-descriptions-item>
          <el-descriptions-item label="支付状态">
            <el-tag :type="getPaymentStatusType(currentOrder.payment_status)">
              {{ currentOrder.payment_status_display }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="支付方式">{{ currentOrder.payment_method_display || '-' }}</el-descriptions-item>
          <el-descriptions-item label="订单总价">¥{{ currentOrder.total_price }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(currentOrder.created_at) }}</el-descriptions-item>
        </el-descriptions>

        <el-descriptions title="物流信息" :column="2" border style="margin-top: 16px;">
          <el-descriptions-item label="快递公司">{{ currentOrder.shipping_company_display || '-' }}</el-descriptions-item>
          <el-descriptions-item label="物流状态">
            <el-tag :type="getShippingStatusType(currentOrder.shipping_status)">
              {{ currentOrder.shipping_status_display }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="快递单号">{{ currentOrder.tracking_no || '-' }}</el-descriptions-item>
          <el-descriptions-item label="发货时间">{{ currentOrder.shipped_at ? formatTime(currentOrder.shipped_at) : '-' }}</el-descriptions-item>
        </el-descriptions>

        <div style="margin-top: 16px;">
          <h4 style="margin-bottom: 12px;">商品明细</h4>
          <el-table :data="currentOrder.items" border size="small">
            <el-table-column label="商品名称" prop="product_name" />
            <el-table-column label="单价" width="100">
              <template #default="{ row }">¥{{ row.price }}</template>
            </el-table-column>
            <el-table-column label="数量" prop="quantity" width="80" />
            <el-table-column label="小计" width="100">
              <template #default="{ row }">¥{{ row.subtotal }}</template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '../../api/admin'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const orders = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const shippingDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const currentOrder = ref(null)
const saving = ref(false)
const shippingForm = ref({
  shipping_company: '',
  shipping_status: '',
  tracking_no: ''
})

const getPaymentStatusType = (status) => {
  const types = { pending: 'warning', paid: 'success' }
  return types[status] || 'info'
}

const getPaymentStatusText = (status) => {
  const texts = { pending: '待支付', paid: '已支付' }
  return texts[status] || status
}

const getShippingStatusType = (status) => {
  const types = { not_shipped: 'info', shipped: 'warning', in_transit: 'primary', arrived: 'success', signed: 'success' }
  return types[status] || 'info'
}

const getShippingStatusText = (status) => {
  const texts = { not_shipped: '未发货', shipped: '已发货', in_transit: '运输中', arrived: '已到达', signed: '已签收' }
  return texts[status] || status
}

const formatTime = (time) => {
  if (!time) return ''
  return time.replace('T', ' ').slice(0, 19)
}

const loadOrders = async () => {
  loading.value = true
  try {
    const res = await adminApi.getOrders({ page: currentPage.value, page_size: pageSize.value })
    orders.value = res.results || []
    total.value = res.count || 0
  } catch (err) {
    ElMessage.error('加载订单失败')
  } finally {
    loading.value = false
  }
}

const handleShip = async (row) => {
  try {
    await adminApi.shipOrder(row.id)
    ElMessage.success('发货成功')
    loadOrders()
  } catch (err) {
    ElMessage.error(err?.response?.data?.error || '发货失败')
  }
}

const openShippingDialog = (row) => {
  currentOrder.value = row
  shippingForm.value = {
    shipping_company: row.shipping_company || '',
    shipping_status: row.shipping_status || 'not_shipped',
    tracking_no: row.tracking_no || ''
  }
  shippingDialogVisible.value = true
}

const saveShipping = async () => {
  saving.value = true
  try {
    await adminApi.updateShipping(currentOrder.value.id, shippingForm.value)
    ElMessage.success('物流信息已更新')
    shippingDialogVisible.value = false
    loadOrders()
  } catch (err) {
    ElMessage.error(err?.response?.data?.error || '更新失败')
  } finally {
    saving.value = false
  }
}

const handleView = (row) => {
  currentOrder.value = row
  detailDialogVisible.value = true
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  loadOrders()
}

onMounted(() => {
  loadOrders()
})
</script>

<style scoped>
.order-manage { padding: 20px; }
.page-header { margin-bottom: 20px; }
.page-header h1 { margin: 0; font-size: 24px; color: #303133; }
.pagination { margin-top: 20px; display: flex; justify-content: flex-end; }
.order-detail { padding: 10px 0; }
</style>
