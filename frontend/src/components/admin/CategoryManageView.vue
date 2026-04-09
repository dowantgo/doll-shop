<template>
  <div class="category-manage">
    <div class="page-header">
      <h1>分类管理</h1>
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon>
        添加分类
      </el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="safeCategories" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="分类名称" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑分类' : '添加分类'" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { adminApi } from '../../api/admin'
import { normalizeList } from '../../utils/api-normalize'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const categories = ref({})
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const form = ref({ name: '', description: '' })

const safeCategories = computed(() => normalizeList(categories.value))

const rules = {
  name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }]
}

const loadCategories = async () => {
  loading.value = true
  try {
    const res = await adminApi.getCategories()
    categories.value = res
  } catch (err) {
    ElMessage.error('加载分类失败')
  } finally {
    loading.value = false
  }
}

const showAddDialog = () => {
  isEdit.value = false
  form.value = { name: '', description: '' }
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  form.value = { id: row.id, name: row.name || '', description: row.description || '' }
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    const countRes = await adminApi.getCategoryProductCount(row.id)
    const productCount = countRes.product_count || 0

    if (productCount > 0) {
      await ElMessageBox.confirm(
        `该分类下有 ${productCount} 个商品，删除分类后将一并删除这些商品，是否确认删除？`,
        '危险操作警告',
        { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消', distinguishCancelAndClose: true }
      )
    } else {
      await ElMessageBox.confirm('确定要删除该分类吗？', '提示', { type: 'warning' })
    }

    await adminApi.deleteCategory(row.id)
    ElMessage.success('删除成功')
    loadCategories()
  } catch (err) {
    if (err !== 'cancel' && err !== 'close') ElMessage.error('删除失败')
  }
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    if (isEdit.value) {
      await adminApi.updateCategory(form.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await adminApi.createCategory(form.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    loadCategories()
  } catch (err) {
    ElMessage.error(isEdit.value ? '更新失败' : '添加失败')
  }
}

onMounted(() => {
  loadCategories()
})
</script>

<style scoped>
.category-manage { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h1 { margin: 0; font-size: 24px; color: #303133; }
</style>
