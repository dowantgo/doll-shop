<template>
  <div class="inventory-manage">
    <div class="page-header">
      <h1>库存管理</h1>
    </div>

    <el-card shadow="never">
      <el-table :data="products" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="图片" width="80">
          <template #default="{ row }">
            <el-image :src="row.image_url" style="width: 50px; height: 50px;" fit="cover" />
          </template>
        </el-table-column>
        <el-table-column prop="name" label="商品名称" />
        <el-table-column prop="stock" label="当前库存" />
        <el-table-column prop="sales_count" label="累计销量" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleAdjust(row)">调整库存</el-button>
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

    <el-dialog v-model="dialogVisible" title="调整库存" width="400px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="商品">
          <span>{{ form.name }}</span>
        </el-form-item>
        <el-form-item label="当前库存">
          <span>{{ form.current_stock }}</span>
        </el-form-item>
        <el-form-item label="新库存">
          <el-input-number v-model="form.new_stock" :min="0" />
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
import { ref, onMounted } from 'vue'
import { adminApi } from '../../api/admin'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const products = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const dialogVisible = ref(false)
const form = ref({ id: null, name: '', current_stock: 0, new_stock: 0 })

const loadProducts = async () => {
  loading.value = true
  try {
    const res = await adminApi.getProducts({ page: currentPage.value, page_size: pageSize.value })
    products.value = res.results || []
    total.value = res.count || 0
  } catch (err) {
    ElMessage.error('加载商品失败')
  } finally {
    loading.value = false
  }
}

const handleAdjust = (row) => {
  form.value = { id: row.id, name: row.name, current_stock: row.stock, new_stock: row.stock }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    await adminApi.adjustStock(form.value.id, { stock: form.value.new_stock })
    ElMessage.success('库存调整成功')
    dialogVisible.value = false
    loadProducts()
  } catch (err) {
    ElMessage.error('调整失败')
  }
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  loadProducts()
}

onMounted(() => {
  loadProducts()
})
</script>

<style scoped>
.inventory-manage { padding: 20px; }
.page-header { margin-bottom: 20px; }
.page-header h1 { margin: 0; font-size: 24px; color: #303133; }
.pagination { margin-top: 20px; display: flex; justify-content: flex-end; }
</style>
