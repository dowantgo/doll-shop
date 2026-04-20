<template>
  <div class="refund-admin">
    <el-card shadow="never" class="panel">
      <template #header>
        <div class="header-row">
          <span>退款审核台</span>
          <div class="filters">
            <el-select v-model="filters.status" clearable placeholder="状态" style="width: 130px" @change="load">
              <el-option value="pending" label="pending" />
              <el-option value="approved" label="approved" />
              <el-option value="rejected" label="rejected" />
              <el-option value="refunding" label="refunding" />
              <el-option value="success" label="success" />
              <el-option value="failed" label="failed" />
            </el-select>
            <el-input v-model="filters.order_id" placeholder="订单号" style="width: 180px" @keyup.enter="load" />
            <el-button type="primary" @click="load">查询</el-button>
          </div>
        </div>
      </template>

      <el-table :data="rows" v-loading="loading" border>
        <el-table-column prop="refund_no" label="退款单号" min-width="180" />
        <el-table-column prop="order_id" label="订单号" min-width="180" />
        <el-table-column prop="product_name" label="商品" min-width="140" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="requested_amount" label="申请金额" width="120" />
        <el-table-column prop="approved_amount" label="审核金额" width="120" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="review_note" label="备注" min-width="160" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'pending'"
              size="small"
              type="success"
              @click="review(row, 'approve')"
            >
              同意
            </el-button>
            <el-button
              v-if="row.status === 'pending'"
              size="small"
              type="danger"
              text
              @click="review(row, 'reject')"
            >
              拒绝
            </el-button>
            <span v-if="row.status !== 'pending'">-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '../../api/admin'

const loading = ref(false)
const rows = ref([])
const filters = reactive({
  status: '',
  order_id: ''
})

const load = async () => {
  loading.value = true
  try {
    const res = await adminApi.getRefunds({
      status: filters.status || undefined,
      order_id: filters.order_id || undefined,
      page_size: 200
    })
    rows.value = res?.results || res || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '获取退款列表失败')
  } finally {
    loading.value = false
  }
}

const review = async (row, action) => {
  try {
    const { value } = await ElMessageBox.prompt(
      action === 'approve' ? '请输入审核备注（可选）' : '请输入拒绝原因',
      action === 'approve' ? '同意退款' : '拒绝退款',
      {
        confirmButtonText: '提交',
        cancelButtonText: '取消',
        inputType: 'textarea',
        inputValue: ''
      }
    )
    await adminApi.reviewRefund(row.id, { action, note: value || '' })
    ElMessage.success('审核完成')
    await load()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e?.response?.data?.error || '审核失败')
    }
  }
}

onMounted(load)
</script>

<style scoped>
.refund-admin {
  display: grid;
  gap: 14px;
}

.panel {
  border-radius: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-weight: 700;
}

.filters {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
</style>
