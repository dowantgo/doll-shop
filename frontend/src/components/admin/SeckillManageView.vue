<template>
  <div class="seckill-manage">
    <div class="page-header">
      <h1>秒杀管理</h1>
      <el-button type="primary" @click="openCreateDialog">新增秒杀活动</el-button>
    </div>

    <div class="stats-grid">
      <el-card shadow="never" v-for="item in statCards" :key="item.key">
        <div class="stat-name">{{ item.label }}</div>
        <div class="stat-value">{{ item.value }}</div>
      </el-card>
    </div>

    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" class="filter-form">
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部" style="width: 140px">
            <el-option label="草稿" value="draft" />
            <el-option label="在线" value="online" />
            <el-option label="已结束" value="ended" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键字">
          <el-input
            v-model="filters.keyword"
            clearable
            placeholder="活动名/商品名"
            style="width: 240px"
            @keyup.enter="loadActivities"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadActivities">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table :data="activities" v-loading="activityLoading" style="width: 100%" empty-text="暂无秒杀活动">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="活动名" min-width="160" />
        <el-table-column prop="product_name" label="商品" min-width="160" />
        <el-table-column label="秒杀价" width="100">
          <template #default="{ row }">¥{{ row.seckill_price }}</template>
        </el-table-column>
        <el-table-column label="库存" min-width="180">
          <template #default="{ row }">
            总 {{ row.total_stock }} / 已占 {{ row.reserved_stock }} / 剩余 {{ row.remaining_stock }}
          </template>
        </el-table-column>
        <el-table-column label="限购" width="90">
          <template #default="{ row }">{{ row.per_user_limit }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间" min-width="260">
          <template #default="{ row }">
            <div>{{ formatDate(row.start_at) }} ~</div>
            <div>{{ formatDate(row.end_at) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="330" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" @click="openStockDialog(row)">调库存</el-button>
            <el-button size="small" @click="openPriceDialog(row)">调价格</el-button>
            <el-dropdown @command="(v) => openStatusDialog(row, v)">
              <el-button size="small" type="warning">改状态</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="draft">草稿</el-dropdown-item>
                  <el-dropdown-item command="online">上线</el-dropdown-item>
                  <el-dropdown-item command="ended">结束</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button size="small" type="danger" @click="removeActivity(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="activityPage"
          v-model:page-size="activityPageSize"
          :total="activityTotal"
          layout="total, prev, pager, next"
          @current-change="loadActivities"
        />
      </div>
    </el-card>

    <el-card shadow="never" class="reservation-card">
      <template #header>
        <div class="section-title">预占记录管理</div>
      </template>

      <el-form :inline="true" class="filter-form">
        <el-form-item label="状态">
          <el-select v-model="reservationFilters.status" clearable placeholder="全部" style="width: 140px">
            <el-option label="预占中" value="reserved" />
            <el-option label="已下单" value="ordered" />
            <el-option label="已支付" value="paid" />
            <el-option label="已取消" value="cancelled" />
            <el-option label="已过期" value="expired" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键字">
          <el-input
            v-model="reservationFilters.keyword"
            clearable
            placeholder="活动/商品/用户名"
            style="width: 240px"
            @keyup.enter="loadReservations"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadReservations">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="reservations" v-loading="reservationLoading" empty-text="暂无预占记录">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="activity_name" label="活动" min-width="150" />
        <el-table-column prop="product_name" label="商品" min-width="140" />
        <el-table-column prop="user_name" label="用户" width="110" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="reservationStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="order_id" label="关联订单" width="170" />
        <el-table-column label="过期时间" min-width="170">
          <template #default="{ row }">{{ formatDate(row.reserved_expires_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              size="small"
              type="danger"
              :disabled="row.status !== 'reserved'"
              @click="releaseReservation(row)"
            >
              释放
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="log-card">
      <template #header>
        <div class="section-title">操作日志（最近50条）</div>
      </template>
      <el-table :data="logs" v-loading="logLoading" empty-text="暂无操作日志">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="action_type" label="动作" width="150" />
        <el-table-column prop="operator_name" label="操作人" width="120" />
        <el-table-column prop="activity_name" label="活动" min-width="160" />
        <el-table-column prop="remark" label="备注" min-width="220" show-overflow-tooltip />
        <el-table-column label="时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="activityDialogVisible" :title="editingId ? '编辑秒杀活动' : '新增秒杀活动'" width="640px">
      <el-form :model="activityForm" label-width="110px">
        <el-form-item label="活动名称">
          <el-input v-model="activityForm.name" maxlength="120" />
        </el-form-item>
        <el-form-item label="关联商品">
          <el-select
            v-if="editingId"
            v-model="activityForm.product"
            filterable
            placeholder="请选择商品"
            style="width: 100%"
          >
            <el-option
              v-for="item in productOptions"
              :key="item.id"
              :label="`${item.id} - ${item.name}`"
              :value="item.id"
            />
          </el-select>
          <el-select
            v-else
            v-model="activityForm.products"
            filterable
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="可多选商品（同一活动）"
            style="width: 100%"
          >
            <el-option
              v-for="item in productOptions"
              :key="item.id"
              :label="`${item.id} - ${item.name}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="秒杀价">
          <el-input-number v-model="activityForm.seckill_price" :min="0.01" :precision="2" :step="1" />
        </el-form-item>
        <el-form-item label="总库存">
          <el-input-number v-model="activityForm.total_stock" :min="1" :step="1" />
        </el-form-item>
        <el-form-item label="每人限购">
          <el-input-number v-model="activityForm.per_user_limit" :min="1" :step="1" />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker
            v-model="activityForm.start_at"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="开始时间"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker
            v-model="activityForm.end_at"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="结束时间"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="activityForm.status" style="width: 160px">
            <el-option label="草稿" value="draft" />
            <el-option label="在线" value="online" />
            <el-option label="已结束" value="ended" />
          </el-select>
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="activityForm.is_enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="activityDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitActivity">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="stockDialogVisible" title="库存调整" width="460px">
      <el-form :model="stockForm" label-width="90px">
        <el-form-item label="调整方式">
          <el-select v-model="stockForm.mode" style="width: 180px">
            <el-option label="设置总库存" value="set" />
            <el-option label="增加库存" value="increase" />
            <el-option label="减少库存" value="decrease" />
          </el-select>
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="stockForm.quantity" :min="1" :step="1" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="stockForm.remark" maxlength="255" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="stockDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitAdjustStock">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="priceDialogVisible" title="价格调整" width="460px">
      <el-form :model="priceForm" label-width="90px">
        <el-form-item label="秒杀价格">
          <el-input-number v-model="priceForm.seckill_price" :min="0.01" :precision="2" :step="1" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="priceForm.remark" maxlength="255" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="priceDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitAdjustPrice">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="statusDialogVisible" title="状态切换" width="460px">
      <el-form :model="statusForm" label-width="90px">
        <el-form-item label="目标状态">
          <el-select v-model="statusForm.status" style="width: 180px">
            <el-option label="草稿" value="draft" />
            <el-option label="在线" value="online" />
            <el-option label="已结束" value="ended" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="statusForm.remark" maxlength="255" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="statusDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitChangeStatus">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '../../api/admin'

const activityLoading = ref(false)
const reservationLoading = ref(false)
const logLoading = ref(false)
const saving = ref(false)

const stats = ref({})
const activities = ref([])
const reservations = ref([])
const logs = ref([])
const productOptions = ref([])

const activityPage = ref(1)
const activityPageSize = ref(10)
const activityTotal = ref(0)

const filters = reactive({
  status: '',
  keyword: ''
})

const reservationFilters = reactive({
  status: '',
  keyword: ''
})

const activityDialogVisible = ref(false)
const editingId = ref(null)
const activityForm = reactive({
  name: '',
  product: null,
  products: [],
  seckill_price: 0,
  total_stock: 1,
  per_user_limit: 1,
  start_at: '',
  end_at: '',
  status: 'draft',
  is_enabled: true
})

const stockDialogVisible = ref(false)
const stockForm = reactive({ mode: 'set', quantity: 1, remark: '' })
const priceDialogVisible = ref(false)
const priceForm = reactive({ seckill_price: 0.01, remark: '' })
const statusDialogVisible = ref(false)
const statusForm = reactive({ status: 'draft', remark: '' })

const currentActivity = ref(null)

const statCards = computed(() => [
  { key: 'a1', label: '活动总数', value: stats.value.activity_total || 0 },
  { key: 'a2', label: '在线活动', value: stats.value.activity_online || 0 },
  { key: 'r1', label: '预占总数', value: stats.value.reservation_total || 0 },
  { key: 'r2', label: '已支付预占', value: stats.value.reservation_paid || 0 },
  { key: 's1', label: '活动总库存', value: stats.value.stock_total || 0 },
  { key: 's2', label: '支付转化率', value: `${stats.value.paid_conversion_rate || 0}%` }
])

const normalizePaged = data => ({
  count: Number(data?.count || 0),
  results: Array.isArray(data?.results) ? data.results : []
})

const statusText = status => {
  if (status === 'online') return '在线'
  if (status === 'ended') return '已结束'
  return '草稿'
}

const statusType = status => {
  if (status === 'online') return 'success'
  if (status === 'ended') return 'danger'
  return 'info'
}

const reservationStatusType = status => {
  if (status === 'paid') return 'success'
  if (status === 'ordered') return 'warning'
  if (status === 'reserved') return ''
  return 'info'
}

const formatDate = val => {
  if (!val) return '-'
  const dt = new Date(val)
  if (Number.isNaN(dt.getTime())) return val
  const y = dt.getFullYear()
  const m = String(dt.getMonth() + 1).padStart(2, '0')
  const d = String(dt.getDate()).padStart(2, '0')
  const hh = String(dt.getHours()).padStart(2, '0')
  const mm = String(dt.getMinutes()).padStart(2, '0')
  const ss = String(dt.getSeconds()).padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}:${ss}`
}

const loadStats = async () => {
  try {
    stats.value = await adminApi.getSeckillStats()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '加载秒杀统计失败')
  }
}

const loadProductOptions = async () => {
  try {
    const res = await adminApi.getProducts({ page: 1, page_size: 200 })
    const list = Array.isArray(res) ? res : (res?.results || [])
    productOptions.value = list
  } catch (e) {
    productOptions.value = []
    ElMessage.error(e?.response?.data?.error || '加载商品列表失败')
  }
}

const loadActivities = async () => {
  activityLoading.value = true
  try {
    const params = {
      page: activityPage.value,
      page_size: activityPageSize.value,
      status: filters.status || undefined,
      keyword: filters.keyword || undefined
    }
    const res = await adminApi.getSeckillActivities(params)
    const norm = normalizePaged(res)
    activities.value = norm.results
    activityTotal.value = norm.count
  } catch (e) {
    activities.value = []
    activityTotal.value = 0
    ElMessage.error(e?.response?.data?.error || '加载秒杀活动失败')
  } finally {
    activityLoading.value = false
  }
}

const loadReservations = async () => {
  reservationLoading.value = true
  try {
    const res = await adminApi.getSeckillReservations({
      page: 1,
      page_size: 20,
      status: reservationFilters.status || undefined,
      keyword: reservationFilters.keyword || undefined
    })
    const norm = normalizePaged(res)
    reservations.value = norm.results
  } catch (e) {
    reservations.value = []
    ElMessage.error(e?.response?.data?.error || '加载预占记录失败')
  } finally {
    reservationLoading.value = false
  }
}

const loadLogs = async () => {
  logLoading.value = true
  try {
    const res = await adminApi.getSeckillActionLogs({ page: 1, page_size: 50 })
    const norm = normalizePaged(res)
    logs.value = norm.results
  } catch (e) {
    logs.value = []
    ElMessage.error(e?.response?.data?.error || '加载操作日志失败')
  } finally {
    logLoading.value = false
  }
}

const resetFilters = () => {
  filters.status = ''
  filters.keyword = ''
  activityPage.value = 1
  loadActivities()
}

const resetActivityForm = () => {
  editingId.value = null
  activityForm.name = ''
  activityForm.product = null
  activityForm.products = []
  activityForm.seckill_price = 0
  activityForm.total_stock = 1
  activityForm.per_user_limit = 1
  activityForm.start_at = ''
  activityForm.end_at = ''
  activityForm.status = 'draft'
  activityForm.is_enabled = true
}

const openCreateDialog = () => {
  resetActivityForm()
  activityDialogVisible.value = true
}

const openEditDialog = row => {
  editingId.value = row.id
  activityForm.name = row.name
  activityForm.product = row.product
  activityForm.products = [row.product]
  activityForm.seckill_price = Number(row.seckill_price)
  activityForm.total_stock = row.total_stock
  activityForm.per_user_limit = row.per_user_limit
  activityForm.start_at = row.start_at
  activityForm.end_at = row.end_at
  activityForm.status = row.status
  activityForm.is_enabled = !!row.is_enabled
  activityDialogVisible.value = true
}

const validateActivityForm = () => {
  if (!activityForm.name.trim()) return '请输入活动名称'
  if (editingId.value) {
    if (!activityForm.product) return '请选择商品'
  } else if (!Array.isArray(activityForm.products) || activityForm.products.length === 0) {
    return '请至少选择一个商品'
  }
  if (!activityForm.start_at || !activityForm.end_at) return '请选择活动时间'
  if (new Date(activityForm.start_at).getTime() >= new Date(activityForm.end_at).getTime()) {
    return '开始时间必须小于结束时间'
  }
  return ''
}

const submitActivity = async () => {
  const message = validateActivityForm()
  if (message) {
    ElMessage.warning(message)
    return
  }

  saving.value = true
  const payload = {
    name: activityForm.name.trim(),
    seckill_price: activityForm.seckill_price,
    total_stock: activityForm.total_stock,
    per_user_limit: activityForm.per_user_limit,
    start_at: activityForm.start_at,
    end_at: activityForm.end_at,
    status: activityForm.status,
    is_enabled: activityForm.is_enabled
  }

  try {
    if (editingId.value) {
      await adminApi.updateSeckillActivity(editingId.value, {
        ...payload,
        product: activityForm.product
      })
      ElMessage.success('秒杀活动更新成功')
    } else {
      await adminApi.createSeckillActivity({
        ...payload,
        products: activityForm.products
      })
      ElMessage.success('秒杀活动创建成功')
    }
    activityDialogVisible.value = false
    await Promise.all([loadStats(), loadActivities(), loadLogs()])
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '保存秒杀活动失败')
  } finally {
    saving.value = false
  }
}

const removeActivity = async row => {
  try {
    await ElMessageBox.confirm(`确定删除活动【${row.name}】吗？`, '提示', { type: 'warning' })
    await adminApi.deleteSeckillActivity(row.id)
    ElMessage.success('删除成功')
    await Promise.all([loadStats(), loadActivities(), loadLogs()])
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e?.response?.data?.error || '删除失败')
    }
  }
}

const openStockDialog = row => {
  currentActivity.value = row
  stockForm.mode = 'set'
  stockForm.quantity = 1
  stockForm.remark = ''
  stockDialogVisible.value = true
}

const submitAdjustStock = async () => {
  if (!currentActivity.value) return
  saving.value = true
  try {
    await adminApi.adjustSeckillStock(currentActivity.value.id, {
      mode: stockForm.mode,
      quantity: stockForm.quantity,
      remark: stockForm.remark
    })
    ElMessage.success('库存调整成功')
    stockDialogVisible.value = false
    await Promise.all([loadStats(), loadActivities(), loadLogs()])
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '库存调整失败')
  } finally {
    saving.value = false
  }
}

const openPriceDialog = row => {
  currentActivity.value = row
  priceForm.seckill_price = Number(row.seckill_price)
  priceForm.remark = ''
  priceDialogVisible.value = true
}

const submitAdjustPrice = async () => {
  if (!currentActivity.value) return
  saving.value = true
  try {
    await adminApi.adjustSeckillPrice(currentActivity.value.id, {
      seckill_price: priceForm.seckill_price,
      remark: priceForm.remark
    })
    ElMessage.success('价格调整成功')
    priceDialogVisible.value = false
    await Promise.all([loadActivities(), loadLogs()])
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '价格调整失败')
  } finally {
    saving.value = false
  }
}

const openStatusDialog = (row, status) => {
  currentActivity.value = row
  statusForm.status = status || row.status
  statusForm.remark = ''
  statusDialogVisible.value = true
}

const submitChangeStatus = async () => {
  if (!currentActivity.value) return
  saving.value = true
  try {
    await adminApi.changeSeckillStatus(currentActivity.value.id, {
      status: statusForm.status,
      remark: statusForm.remark
    })
    ElMessage.success('状态更新成功')
    statusDialogVisible.value = false
    await Promise.all([loadStats(), loadActivities(), loadLogs()])
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '状态更新失败')
  } finally {
    saving.value = false
  }
}

const releaseReservation = async row => {
  try {
    await ElMessageBox.confirm(`确定释放预占 #${row.id} 吗？`, '提示', { type: 'warning' })
    await adminApi.releaseSeckillReservation(row.id, { remark: 'Admin manual release' })
    ElMessage.success('预占释放成功')
    await Promise.all([loadStats(), loadActivities(), loadReservations(), loadLogs()])
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e?.response?.data?.error || '释放失败')
    }
  }
}

onMounted(async () => {
  await Promise.all([
    loadStats(),
    loadProductOptions(),
    loadActivities(),
    loadReservations(),
    loadLogs()
  ])
})
</script>

<style scoped>
.seckill-manage {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.stat-name {
  color: #909399;
  font-size: 13px;
}

.stat-value {
  margin-top: 6px;
  font-size: 22px;
  font-weight: 700;
  color: #303133;
}

.filter-card {
  margin-bottom: 16px;
}

.filter-form {
  margin-bottom: -18px;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.reservation-card,
.log-card {
  margin-top: 16px;
}

.section-title {
  font-weight: 700;
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }
}
</style>
