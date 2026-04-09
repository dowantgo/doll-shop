<template>
  <div class="user-manage">
    <div class="page-header">
      <h1>用户管理</h1>
    </div>

    <el-card shadow="never">
      <el-table :data="users" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="phone" label="电话" />
        <el-table-column prop="role" label="角色">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'info'">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '正常' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="date_joined" label="注册时间">
          <template #default="{ row }">{{ new Date(row.date_joined).toLocaleString('zh-CN') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button v-if="row.role !== 'admin' && row.is_active" type="warning" size="small" @click="handleSetAdmin(row)">升管理员</el-button>
            <el-button v-if="row.role === 'admin' && !row.is_superuser" type="info" size="small" @click="handleSetUser(row)">降为用户</el-button>
            <el-button v-if="row.is_active && !row.is_superuser" type="danger" size="small" @click="handleDisable(row)">禁用</el-button>
            <el-button v-if="!row.is_active && !row.is_superuser" type="success" size="small" @click="handleEnable(row)">启用</el-button>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '../../api/admin'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const users = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const loadUsers = async () => {
  loading.value = true
  try {
    const res = await adminApi.getUsers({ page: currentPage.value, page_size: pageSize.value })
    users.value = res.results || []
    total.value = res.count || 0
  } catch (err) {
    ElMessage.error('加载用户失败')
  } finally {
    loading.value = false
  }
}

const handleSetAdmin = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要将 "${row.username}" 设为管理员吗？`, '提示', { type: 'warning' })
    await adminApi.setUserAdmin(row.id)
    ElMessage.success('设置成功')
    loadUsers()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error('设置失败')
  }
}

const handleSetUser = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要将 "${row.username}" 降为普通用户吗？`, '提示', { type: 'warning' })
    await adminApi.setUserRole(row.id)
    ElMessage.success('设置成功')
    loadUsers()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error('设置失败')
  }
}

const handleDisable = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要禁用 "${row.username}" 吗？`, '提示', { type: 'warning' })
    await adminApi.disableUser(row.id)
    ElMessage.success('禁用成功')
    loadUsers()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error('禁用失败')
  }
}

const handleEnable = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要启用 "${row.username}" 吗？`, '提示', { type: 'warning' })
    await adminApi.enableUser(row.id)
    ElMessage.success('启用成功')
    loadUsers()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error('启用失败')
  }
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  loadUsers()
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.user-manage { padding: 20px; }
.page-header { margin-bottom: 20px; }
.page-header h1 { margin: 0; font-size: 24px; color: #303133; }
.pagination { margin-top: 20px; display: flex; justify-content: flex-end; }
</style>
