﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿<template>
  <div class="product-manage">
    <div class="page-header">
      <h1>商品管理</h1>
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon>
        添加商品
      </el-button>
    </div>

    <el-card class="filter-card" shadow="never">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="关键词">
          <el-input v-model="filterForm.keyword" placeholder="商品名称" clearable />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="filterForm.category" placeholder="全部分类" clearable>
            <el-option
              v-for="cat in safeCategories"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table :data="products" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="图片" width="80">
          <template #default="{ row }">
            <el-image
              v-if="getMainImage(row)"
              :src="getMainImage(row)"
              :preview-src-list="getImageList(row)"
              style="width: 50px; height: 50px;"
              fit="cover"
            />
            <span v-else style="color:#909399;font-size:12px;">无图</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="商品名称" />
        <el-table-column prop="category_name" label="分类" />
        <el-table-column prop="price" label="价格">
          <template #default="{ row }">
            ￥{{ row.price }}
          </template>
        </el-table-column>
        <el-table-column prop="stock" label="库存" />
        <el-table-column prop="sales" label="销量" />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑商品' : '添加商品'"
      width="600px"
      destroy-on-close
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="form.category" placeholder="选择分类">
            <el-option
              v-for="cat in safeCategories"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="价格" prop="price">
          <el-input-number v-model="form.price" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="库存" prop="stock">
          <el-input-number v-model="form.stock" :min="0" />
        </el-form-item>
        <el-form-item label="图片" prop="images">
          <div class="image-upload-area">
            <el-upload
              v-model:file-list="form.imageList"
              action="#"
              :auto-upload="false"
              :on-change="handleImageChange"
              :on-remove="handleImageRemove"
              list-type="picture-card"
              :limit="5"
            >
              <el-icon><Plus /></el-icon>
            </el-upload>
          </div>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" rows="4" />
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
import { ref, onMounted, nextTick, computed } from 'vue'
import { adminApi } from '../../api/admin'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const products = ref([])
const categories = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const filterForm = ref({
  keyword: '',
  category: ''
})

const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const form = ref({
  name: '',
  category: '',
  price: 0,
  stock: 0,
  image_url: '',
  description: '',
  imageList: []
})

const rules = {
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  price: [{ required: true, message: '请输入价格', trigger: 'blur' }],
  stock: [{ required: true, message: '请输入库存', trigger: 'blur' }]
}

const safeCategories = computed(() =>
  Array.isArray(categories.value) ? categories.value.filter(c => c && c.id) : []
)

const getMainImage = product => {
  const imgs = product?.images || []
  const main = imgs.find(i => i.is_main) || imgs[0]
  return main?.image_url || ''
}

const getImageList = product => {
  const imgs = product?.images || []
  return imgs.map(i => i.image_url).filter(url => url)
}

const loadProducts = async () => {
  loading.value = true
  try {
    const res = await adminApi.getProducts({
      page: currentPage.value,
      page_size: pageSize.value,
      search: filterForm.value.keyword,
      category: filterForm.value.category
    })
    products.value = res?.results || []
    total.value = res?.count || 0
  } catch (err) {
    ElMessage.error('加载商品失败')
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  try {
    const res = await adminApi.getCategories()
    categories.value = Array.isArray(res) ? res : (res?.results || [])
  } catch (err) {
    categories.value = []
    console.error('加载分类失败', err)
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadProducts()
}

const resetFilter = () => {
  filterForm.value = { keyword: '', category: '' }
  handleSearch()
}

const handleSizeChange = val => {
  pageSize.value = val
  loadProducts()
}

const handleCurrentChange = val => {
  currentPage.value = val
  loadProducts()
}

const handleImageChange = (file, fileList) => {
  form.value.imageList = fileList
}

const handleImageRemove = (file, fileList) => {
  form.value.imageList = fileList
}

const uploadImage = async (productId) => {
  if (form.value.imageList.length === 0) return

  const failed = []
  for (const fileItem of form.value.imageList) {
    if (fileItem.raw) {
      const formData = new FormData()
      formData.append('image', fileItem.raw)
      formData.append('is_main', fileItem.raw === form.value.imageList[0]?.raw)
      try {
        await adminApi.uploadProductImage(productId, formData)
      } catch (err) {
        failed.push(fileItem.name || '未命名图片')
      }
    }
  }

  if (failed.length > 0) {
    throw new Error(`以下图片上传失败：${failed.join('，')}`)
  }
}

const showAddDialog = () => {
  isEdit.value = false
  form.value = {
    name: '',
    category: null,
    price: 0,
    stock: 0,
    image_url: '',
    description: '',
    imageList: []
  }
  nextTick(() => {
    dialogVisible.value = true
  })
}

const handleEdit = row => {
  isEdit.value = true
  form.value = {
    id: row.id,
    name: row.name || '',
    category: row.category || null,
    price: row.price ?? 0,
    stock: row.stock ?? 0,
    image_url: row.image_url || '',
    description: row.description || '',
    imageList: []
  }
  nextTick(() => {
    dialogVisible.value = true
  })
}

const handleDelete = async row => {
  try {
    await ElMessageBox.confirm('确定要删除该商品吗？', '提示', {
      type: 'warning'
    })
    await adminApi.deleteProduct(row.id)
    ElMessage.success('删除成功')
    loadProducts()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    if (isEdit.value) {
      await adminApi.updateProduct(form.value.id, form.value)
      if (form.value.imageList.length > 0) {
        await uploadImage(form.value.id)
      }
      ElMessage.success('更新成功')
    } else {
      const res = await adminApi.createProduct(form.value)
      if (form.value.imageList.length > 0) {
        await uploadImage(res.id)
      }
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    await loadProducts()
  } catch (err) {
    ElMessage.error(err?.message || (isEdit.value ? '更新失败' : '添加失败'))
  }
}

onMounted(() => {
  loadProducts()
  loadCategories()
})
</script>

<style scoped>
.product-manage {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.filter-card {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
