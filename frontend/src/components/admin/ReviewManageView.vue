<template>
  <div class="review-manage">
    <div class="page-header">
      <h1>评价审核</h1>
    </div>

    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" class="filter-form">
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 140px">
            <el-option label="待审核" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已拒绝" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item label="商品ID">
          <el-input v-model="filters.product_id" placeholder="商品ID" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="用户ID">
          <el-input v-model="filters.user_id" placeholder="用户ID" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="商品名/用户名/评价内容"
            clearable
            style="width: 260px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table :data="reviews" v-loading="loading" style="width: 100%" empty-text="暂无评价数据">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="product_name" label="商品名" min-width="140" />
        <el-table-column prop="user_name" label="用户名" min-width="120" />
        <el-table-column label="评分" width="120">
          <template #default="{ row }">
            <el-rate :model-value="row.rating" disabled size="small" />
          </template>
        </el-table-column>
        <el-table-column prop="content" label="评价内容" min-width="260" show-overflow-tooltip />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="audit_remark" label="审核备注" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openAuditDialog(row)">审核</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadReviews"
        />
      </div>
    </el-card>

    <el-dialog v-model="auditDialogVisible" title="评价审核" width="520px">
      <el-form :model="auditForm" label-width="90px">
        <el-form-item label="审核结果">
          <el-radio-group v-model="auditForm.status">
            <el-radio label="approved">通过</el-radio>
            <el-radio label="rejected">拒绝</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="审核备注">
          <el-input
            v-model="auditForm.audit_remark"
            type="textarea"
            :rows="4"
            maxlength="255"
            show-word-limit
            placeholder="请输入审核备注（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="auditDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitAudit">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '../../api/admin'

const loading = ref(false)
const saving = ref(false)
const reviews = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const filters = reactive({
  status: '',
  product_id: '',
  user_id: '',
  keyword: ''
})

const auditDialogVisible = ref(false)
const currentReviewId = ref(null)
const auditForm = reactive({
  status: 'approved',
  audit_remark: ''
})

const buildQueryParams = () => {
  const params = {
    page: currentPage.value,
    page_size: pageSize.value
  }
  if (filters.status) params.status = filters.status
  if (filters.product_id) params.product_id = filters.product_id
  if (filters.user_id) params.user_id = filters.user_id
  if (filters.keyword) params.keyword = filters.keyword
  return params
}

const normalizeList = (data) => {
  if (Array.isArray(data)) {
    return { results: data, count: data.length }
  }
  return {
    results: Array.isArray(data?.results) ? data.results : [],
    count: Number(data?.count || 0)
  }
}

const loadReviews = async () => {
  loading.value = true
  try {
    const res = await adminApi.getReviews(buildQueryParams())
    const normalized = normalizeList(res)
    reviews.value = normalized.results
    total.value = normalized.count
  } catch (error) {
    reviews.value = []
    total.value = 0
    ElMessage.error(error?.response?.data?.error || '加载评价列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadReviews()
}

const handleReset = () => {
  filters.status = ''
  filters.product_id = ''
  filters.user_id = ''
  filters.keyword = ''
  currentPage.value = 1
  loadReviews()
}

const openAuditDialog = (row) => {
  currentReviewId.value = row.id
  auditForm.status = row.status === 'rejected' ? 'rejected' : 'approved'
  auditForm.audit_remark = row.audit_remark || ''
  auditDialogVisible.value = true
}

const submitAudit = async () => {
  if (!currentReviewId.value) return
  saving.value = true
  try {
    await adminApi.auditReview(currentReviewId.value, {
      status: auditForm.status,
      audit_remark: auditForm.audit_remark
    })
    ElMessage.success('审核成功')
    auditDialogVisible.value = false
    loadReviews()
  } catch (error) {
    ElMessage.error(error?.response?.data?.error || '审核失败')
  } finally {
    saving.value = false
  }
}

const getStatusText = (status) => {
  if (status === 'approved') return '已通过'
  if (status === 'rejected') return '已拒绝'
  return '待审核'
}

const getStatusType = (status) => {
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'danger'
  return 'warning'
}

const formatTime = (value) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  const ss = String(date.getSeconds()).padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}:${ss}`
}

onMounted(() => {
  loadReviews()
})
</script>

<style scoped>
.review-manage {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.filter-card {
  margin-bottom: 16px;
}

.filter-form {
  margin-bottom: -18px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
