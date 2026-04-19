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
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { orderApi } from '../api/order'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const order = ref(null)

const load = async () => {
  loading.value = true
  try {
    const res = await orderApi.getOrderDetail(route.params.id)
    order.value = res
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '获取订单详情失败')
    router.back()
  } finally {
    loading.value = false
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
</style>
