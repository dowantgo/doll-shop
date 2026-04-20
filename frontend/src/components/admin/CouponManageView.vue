<template>
  <div class="coupon-admin">
    <el-card shadow="never" class="panel">
      <template #header>
        <div class="header-row">
          <span>优惠券模板管理</span>
          <el-button type="primary" @click="openCreate">新增模板</el-button>
        </div>
      </template>

      <el-table :data="templates" v-loading="loading" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="模板名" min-width="150" />
        <el-table-column prop="discount_amount" label="减免金额" width="120" />
        <el-table-column prop="min_spend_amount" label="最低消费" width="120" />
        <el-table-column prop="claimed_count" label="已领取" width="100" />
        <el-table-column prop="total_quota" label="总额度" width="100" />
        <el-table-column prop="per_user_limit" label="每人限领" width="100" />
        <el-table-column prop="status" label="状态" width="90" />
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="success" @click="openIssue(row)">发放</el-button>
            <el-button size="small" type="danger" text @click="removeTemplate(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑模板' : '新增模板'" width="520px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="模板名"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="减免金额"><el-input-number v-model="form.discount_amount" :min="0" :step="1" /></el-form-item>
        <el-form-item label="最低消费"><el-input-number v-model="form.min_spend_amount" :min="0" :step="1" /></el-form-item>
        <el-form-item label="总额度"><el-input-number v-model="form.total_quota" :min="0" :step="1" /></el-form-item>
        <el-form-item label="每人限领"><el-input-number v-model="form.per_user_limit" :min="1" :step="1" /></el-form-item>
        <el-form-item label="有效期开始"><el-date-picker v-model="form.valid_from" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" /></el-form-item>
        <el-form-item label="有效期结束"><el-date-picker v-model="form.valid_to" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status">
            <el-option value="active" label="active" />
            <el-option value="inactive" label="inactive" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="issueVisible" title="发放优惠券" width="420px">
      <el-form :model="issueForm" label-width="100px">
        <el-form-item label="模板ID">
          <el-input v-model="issueForm.template_id" disabled />
        </el-form-item>
        <el-form-item label="用户ID列表">
          <el-input v-model="issueForm.user_ids_text" placeholder="例如：1,2,3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="issueVisible = false">取消</el-button>
        <el-button type="primary" :loading="issuing" @click="submitIssue">发放</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '../../api/admin'

const loading = ref(false)
const saving = ref(false)
const issuing = ref(false)
const templates = ref([])
const dialogVisible = ref(false)
const issueVisible = ref(false)

const form = reactive({
  id: null,
  name: '',
  discount_amount: 10,
  min_spend_amount: 50,
  total_quota: 100,
  per_user_limit: 1,
  valid_from: '',
  valid_to: '',
  status: 'active'
})

const issueForm = reactive({
  template_id: null,
  user_ids_text: ''
})

const resetForm = () => {
  form.id = null
  form.name = ''
  form.discount_amount = 10
  form.min_spend_amount = 50
  form.total_quota = 100
  form.per_user_limit = 1
  form.valid_from = ''
  form.valid_to = ''
  form.status = 'active'
}

const load = async () => {
  loading.value = true
  try {
    const res = await adminApi.getCouponTemplates({ page_size: 200 })
    templates.value = res?.results || res || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '获取模板失败')
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const openEdit = row => {
  form.id = row.id
  form.name = row.name
  form.discount_amount = Number(row.discount_amount)
  form.min_spend_amount = Number(row.min_spend_amount)
  form.total_quota = Number(row.total_quota)
  form.per_user_limit = Number(row.per_user_limit)
  form.valid_from = row.valid_from?.slice(0, 19) || ''
  form.valid_to = row.valid_to?.slice(0, 19) || ''
  form.status = row.status
  dialogVisible.value = true
}

const save = async () => {
  saving.value = true
  try {
    const payload = {
      name: form.name,
      coupon_type: 'fixed',
      discount_amount: form.discount_amount,
      min_spend_amount: form.min_spend_amount,
      total_quota: form.total_quota,
      per_user_limit: form.per_user_limit,
      valid_from: form.valid_from,
      valid_to: form.valid_to,
      status: form.status
    }
    if (form.id) {
      await adminApi.updateCouponTemplate(form.id, payload)
    } else {
      await adminApi.createCouponTemplate(payload)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '保存失败')
  } finally {
    saving.value = false
  }
}

const removeTemplate = async row => {
  try {
    await ElMessageBox.confirm(`确认删除模板「${row.name}」吗？`, '提示', { type: 'warning' })
    await adminApi.deleteCouponTemplate(row.id)
    ElMessage.success('删除成功')
    await load()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.error || '删除失败')
  }
}

const openIssue = row => {
  issueForm.template_id = row.id
  issueForm.user_ids_text = ''
  issueVisible.value = true
}

const submitIssue = async () => {
  issuing.value = true
  try {
    const ids = issueForm.user_ids_text
      .split(',')
      .map(x => Number(x.trim()))
      .filter(x => Number.isInteger(x) && x > 0)
    if (!ids.length) {
      ElMessage.warning('请填写至少一个用户ID')
      return
    }
    const res = await adminApi.issueCoupons({
      template_id: issueForm.template_id,
      user_ids: ids
    })
    ElMessage.success(`发放完成：成功 ${res.issued_count}，跳过 ${res.skipped_count}`)
    issueVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '发放失败')
  } finally {
    issuing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.coupon-admin {
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
  font-weight: 700;
}
</style>
