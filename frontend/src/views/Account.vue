﻿﻿﻿<template>
  <div class="account-page">
    <el-card shadow="never">
      <template #header>
        <div class="header">个人中心</div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="基本信息" name="info">
          <div v-if="user" class="info">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="用户名">{{ user.username }}</el-descriptions-item>
              <el-descriptions-item label="邮箱">{{ user.email }}</el-descriptions-item>
              <el-descriptions-item label="电话">{{ user.phone || '-' }}</el-descriptions-item>
              <el-descriptions-item label="角色">
                <el-tag :type="user.role === 'admin' ? 'danger' : 'primary'">{{ user.role }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ user.created_at }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <el-empty v-else description="暂无用户信息" />
        </el-tab-pane>

        <el-tab-pane label="收货地址" name="address">
          <div class="address-wrap">
            <el-card shadow="never" class="address-card" :body-style="{ paddingBottom: '0' }">
              <template #header>
                <div class="address-header">
                  地址管理
                  <el-button type="primary" size="small" @click="startCreate">新增地址</el-button>
                </div>
              </template>

              <el-table :data="addresses" style="width: 100%" empty-text="暂无地址">
                <el-table-column label="名称" prop="name" width="140" />
                <el-table-column label="电话" prop="phone" width="160" />
                <el-table-column label="地址" min-width="360">
                  <template #default="{ row }">
                    {{ row.province }}{{ row.city }}{{ row.district }} {{ row.address }}
                  </template>
                </el-table-column>
                <el-table-column label="默认" width="110">
                  <template #default="{ row }">
                    <el-tag v-if="row.is_default" type="success">是</el-tag>
                    <el-tag v-else>否</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="220">
                  <template #default="{ row }">
                    <el-button size="small" @click="startEdit(row)">编辑</el-button>
                    <el-button size="small" type="danger" text @click="removeAddress(row.id)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>

            <el-divider />

            <el-card shadow="never" class="form-card">
              <template #header>
                <div class="address-header">{{ formMode === 'edit' ? '编辑地址' : '新增地址' }}</div>
              </template>

              <el-form :model="form" label-width="90px">
                <el-form-item label="收货人">
                  <el-input v-model="form.name" />
                </el-form-item>
                <el-form-item label="电话">
                  <el-input v-model="form.phone" />
                </el-form-item>
                <el-form-item label="省">
                  <el-select
                    v-model="locationCodes.province"
                    placeholder="请选择省"
                    filterable
                    class="region-select"
                    @change="onProvinceChange"
                  >
                    <el-option v-for="p in provinceOptions" :key="p.value" :label="p.label" :value="p.value" />
                  </el-select>
                </el-form-item>
                <el-form-item label="市">
                  <el-select
                    v-model="locationCodes.city"
                    placeholder="请先选择省"
                    filterable
                    :disabled="!locationCodes.province"
                    class="region-select"
                    @change="onCityChange"
                  >
                    <el-option v-for="c in cityOptions" :key="c.value" :label="c.label" :value="c.value" />
                  </el-select>
                </el-form-item>
                <el-form-item label="区县">
                  <el-select
                    v-model="locationCodes.district"
                    placeholder="请先选择市"
                    filterable
                    :disabled="!locationCodes.city"
                    class="region-select"
                    @change="onDistrictChange"
                  >
                    <el-option v-for="d in districtOptions" :key="d.value" :label="d.label" :value="d.value" />
                  </el-select>
                </el-form-item>
                <el-form-item label="详细地址">
                  <el-input v-model="form.address" />
                </el-form-item>
                <el-form-item label="是否默认">
                  <el-switch v-model="form.is_default" />
                </el-form-item>

                <el-form-item>
                  <el-button type="primary" :loading="saving" @click="submitAddress">
                    {{ formMode === 'edit' ? '保存' : '创建' }}
                  </el-button>
                  <el-button text @click="cancelForm">取消</el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </div>
        </el-tab-pane>

        <el-tab-pane label="我的评价" name="reviews">
          <el-card shadow="never">
            <template #header>
              <div class="review-header">
                我的评价
                <el-button size="small" @click="loadMyReviews">刷新</el-button>
              </div>
            </template>

            <div v-loading="myReviewLoading">
              <el-alert
                v-if="myReviewError"
                :title="myReviewError"
                type="error"
                :closable="false"
                show-icon
                class="review-alert"
              />

              <el-empty v-else-if="myReviews.length === 0" description="暂无评价记录" />

              <el-table v-else :data="myReviews" style="width: 100%" empty-text="暂无评价记录">
                <el-table-column label="商品" prop="product_name" min-width="180" />
                <el-table-column label="评分" width="120">
                  <template #default="{ row }">
                    <el-rate :model-value="row.rating" disabled size="small" />
                  </template>
                </el-table-column>
                <el-table-column label="状态" width="120">
                  <template #default="{ row }">
                    <el-tag :type="reviewStatusType(row.status)">
                      {{ reviewStatusText(row.status) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="评价内容" min-width="300">
                  <template #default="{ row }">
                    <div class="review-content">{{ row.content || '-' }}</div>
                  </template>
                </el-table-column>
                <el-table-column label="时间" min-width="170">
                  <template #default="{ row }">
                    {{ formatDate(row.created_at) }}
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { regionData } from 'element-china-area-data'
import { reviewApi } from '../api/review'
import { userApi } from '../api/user'

const activeTab = ref('info')
const user = ref(null)
const addresses = ref([])

const formMode = ref('create')
const editingId = ref(null)
const saving = ref(false)

const form = reactive({
  name: '',
  phone: '',
  province: '',
  city: '',
  district: '',
  address: '',
  is_default: false
})

const locationCodes = reactive({
  province: '',
  city: '',
  district: ''
})

const provinceOptions = regionData
const cityOptions = ref([])
const districtOptions = ref([])
const myReviews = ref([])
const myReviewLoading = ref(false)
const myReviewError = ref('')

const findNodeByCode = (list, code) => list.find(item => item.value === code)
const getLabelByCode = (list, code) => findNodeByCode(list, code)?.label || ''

const onProvinceChange = provinceCode => {
  const province = findNodeByCode(provinceOptions, provinceCode)
  cityOptions.value = province?.children || []
  districtOptions.value = []

  locationCodes.city = ''
  locationCodes.district = ''

  form.province = province?.label || ''
  form.city = ''
  form.district = ''
}

const onCityChange = cityCode => {
  const city = findNodeByCode(cityOptions.value, cityCode)
  districtOptions.value = city?.children || []

  locationCodes.district = ''

  form.city = city?.label || ''
  form.district = ''
}

const onDistrictChange = districtCode => {
  form.district = getLabelByCode(districtOptions.value, districtCode)
}

const resetLocationOptions = () => {
  cityOptions.value = []
  districtOptions.value = []
  locationCodes.province = ''
  locationCodes.city = ''
  locationCodes.district = ''
}

const hydrateLocationByText = () => {
  resetLocationOptions()

  const province = provinceOptions.find(p => p.label === form.province)
  if (!province) return

  locationCodes.province = province.value
  cityOptions.value = province.children || []

  const city = cityOptions.value.find(c => c.label === form.city)
  if (!city) return

  locationCodes.city = city.value
  districtOptions.value = city.children || []

  const district = districtOptions.value.find(d => d.label === form.district)
  if (district) {
    locationCodes.district = district.value
  }
}

const loadUser = async () => {
  try {
    user.value = await userApi.getUserInfo()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '获取用户信息失败')
  }
}

const loadAddresses = async () => {
  try {
    const res = await userApi.getAddresses()
    addresses.value = res?.results || res || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '获取地址失败')
  }
}

const loadMyReviews = async () => {
  myReviewLoading.value = true
  myReviewError.value = ''
  try {
    const res = await reviewApi.getMyReviews({ page: 1, page_size: 20 })
    myReviews.value = res.results
  } catch (e) {
    myReviews.value = []
    myReviewError.value = e?.response?.data?.error || '获取我的评价失败'
    ElMessage.error(myReviewError.value)
  } finally {
    myReviewLoading.value = false
  }
}

const reviewStatusText = status => {
  if (status === 'rejected') return '已隐藏'
  return '已发布'
}

const reviewStatusType = status => {
  if (status === 'rejected') return 'danger'
  return 'success'
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

const resetForm = () => {
  editingId.value = null
  formMode.value = 'create'
  form.name = ''
  form.phone = ''
  form.province = ''
  form.city = ''
  form.district = ''
  form.address = ''
  form.is_default = false
  resetLocationOptions()
}

const startCreate = () => {
  activeTab.value = 'address'
  resetForm()
}

const startEdit = row => {
  activeTab.value = 'address'
  formMode.value = 'edit'
  editingId.value = row.id

  form.name = row.name || ''
  form.phone = row.phone || ''
  form.province = row.province || ''
  form.city = row.city || ''
  form.district = row.district || ''
  form.address = row.address || ''
  form.is_default = !!row.is_default

  hydrateLocationByText()
}

const cancelForm = () => {
  resetForm()
}

const submitAddress = async () => {
  saving.value = true
  try {
    const payload = {
      name: form.name,
      phone: form.phone,
      province: form.province,
      city: form.city,
      district: form.district,
      address: form.address,
      is_default: form.is_default
    }

    if (formMode.value === 'edit') {
      await userApi.updateAddress(editingId.value, payload)
      ElMessage.success('地址已保存')
    } else {
      await userApi.createAddress(payload)
      ElMessage.success('地址已创建')
    }

    await loadAddresses()
    resetForm()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || e?.response?.data || '保存失败')
  } finally {
    saving.value = false
  }
}

const removeAddress = async id => {
  try {
    await userApi.deleteAddress(id)
    ElMessage.success('地址已删除')
    await loadAddresses()
    if (formMode.value === 'edit' && editingId.value === id) resetForm()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '删除失败')
  }
}

onMounted(async () => {
  await Promise.all([loadUser(), loadAddresses(), loadMyReviews()])
})
</script>

<style scoped>
.account-page {
  padding: 8px;
}

.header {
  font-weight: 800;
  color: #23354d;
}

.address-wrap {
  padding-top: 10px;
}

.address-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.review-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.review-alert {
  margin-bottom: 12px;
}

.review-content {
  line-height: 1.5;
  color: #303133;
}

.form-card {
  margin-top: 8px;
}

.region-select {
  width: 100%;
}

:deep(.el-tabs__item) {
  font-weight: 600;
}

:deep(.el-descriptions__label) {
  width: 110px;
  color: #4f5f73;
}
</style>
