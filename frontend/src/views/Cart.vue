<template>
  <div class="cart-page">
    <el-row :gutter="16">
      <el-col :span="16">
        <el-card shadow="never" class="cart-card">
          <template #header>
            <div class="header">我的购物车</div>
          </template>

          <el-table :data="items" style="width: 100%" empty-text="购物车为空">
            <el-table-column label="商品" width="420">
              <template #default="{ row }">
                <div class="item-cell">
                  <img v-if="row.product_image" class="thumb" :src="row.product_image" alt="" @error="onImgError" />
                  <div class="item-info">
                    <div class="item-name" :title="row.product_name">{{ row.product_name }}</div>
                    <div class="item-price">单价：¥{{ row.product_price }}</div>
                  </div>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="数量" width="260">
              <template #default="{ row }">
                <div class="qty-row">
                  <el-input-number
                    v-model="row.quantity"
                    :min="1"
                    :max="row.product_stock || 9999"
                    size="small"
                  />
                  <el-button size="small" @click="updateQty(row)">更新</el-button>
                  <el-button size="small" type="danger" text @click="removeItem(row)">移除</el-button>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="小计" width="180">
              <template #default="{ row }">¥{{ row.subtotal }}</template>
            </el-table-column>
          </el-table>

          <div class="summary">
            <div>总数量：{{ totalQuantity }}</div>
            <div class="total">合计：¥{{ totalPrice }}</div>
            <el-button :disabled="items.length === 0" @click="clearCart">清空购物车</el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never" class="checkout-card">
          <template #header>
            <div class="checkout-title">结算</div>
          </template>

          <el-form :model="checkout" label-width="90px">
            <el-form-item label="优惠券">
              <el-select
                v-model="checkout.couponId"
                placeholder="可选，最多使用1张"
                style="width: 100%"
                clearable
                :disabled="coupons.length === 0"
                @change="loadPreview"
              >
                <el-option
                  v-for="c in coupons"
                  :key="c.id"
                  :value="c.id"
                  :label="`${c.template.name}（减¥${c.template.discount_amount}，满¥${c.template.min_spend_amount}）`"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="优惠试算">
              <div class="preview-box" v-loading="previewLoading">
                <div class="preview-row">
                  <span>商品总额</span>
                  <strong>¥{{ preview.subtotal_amount || totalPrice }}</strong>
                </div>
                <div class="preview-row">
                  <span>满减优惠</span>
                  <strong>-¥{{ preview.full_reduction_amount || '0.00' }}</strong>
                </div>
                <div class="preview-row">
                  <span>券优惠</span>
                  <strong>-¥{{ preview.coupon_discount_amount || '0.00' }}</strong>
                </div>
                <div class="preview-row total-row">
                  <span>应付总额</span>
                  <strong>¥{{ preview.final_payable_amount || totalPrice }}</strong>
                </div>
                <div v-if="preview.coupon_error" class="preview-error">{{ preview.coupon_error }}</div>
              </div>
            </el-form-item>

            <el-form-item label="收货地址">
              <el-select
                v-model="checkout.addressId"
                placeholder="请选择地址"
                style="width: 100%"
                :disabled="addresses.length === 0"
              >
                <el-option
                  v-for="a in addresses"
                  :key="a.id"
                  :value="a.id"
                  :label="`${a.name} - ${a.province}${a.city}${a.district} ${a.address}`"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="备注">
              <el-input v-model="checkout.remark" type="textarea" :rows="4" placeholder="选填" />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :loading="checkoutLoading"
                :disabled="items.length === 0 || !checkout.addressId"
                @click="createOrder"
              >
                生成订单
              </el-button>
              <el-button text @click="goOrders">查看订单</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { cartApi } from '../api/cart'
import { couponApi } from '../api/coupon'
import { userApi } from '../api/user'
import { orderApi } from '../api/order'

const router = useRouter()

const items = ref([])
const totalQuantity = ref(0)
const totalPrice = ref('0.00')

const addresses = ref([])
const coupons = ref([])
const preview = ref({
  subtotal_amount: '0.00',
  full_reduction_amount: '0.00',
  coupon_discount_amount: '0.00',
  final_payable_amount: '0.00',
  coupon_error: ''
})
const previewLoading = ref(false)
const defaultImage = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320"><rect width="100%" height="100%" fill="%23f2f3f5"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="%2390999f" font-size="20">No Image</text></svg>'

const checkout = reactive({
  addressId: null,
  remark: '',
  couponId: null
})

const checkoutLoading = ref(false)

const onImgError = event => {
  if (!event?.target) return
  event.target.src = defaultImage
}

const loadCart = async () => {
  try {
    const res = await cartApi.getCart()
    items.value = res?.items || []
    totalQuantity.value = res?.total_quantity || 0
    totalPrice.value = res?.total_price || '0.00'

    if (addresses.value.length && !checkout.addressId) {
      const def = addresses.value.find(a => a.is_default) || addresses.value[0]
      checkout.addressId = def?.id || null
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '获取购物车失败')
  }
}

const loadAddresses = async () => {
  try {
    const res = await userApi.getAddresses()
    addresses.value = res?.results || res || []
    if (addresses.value.length && !checkout.addressId) {
      const def = addresses.value.find(a => a.is_default) || addresses.value[0]
      checkout.addressId = def?.id || null
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '获取收货地址失败')
  }
}

const loadCoupons = async () => {
  try {
    const res = await couponApi.getMyCoupons({ status: 'unused' })
    coupons.value = res?.results || res || []
  } catch (e) {
    coupons.value = []
  }
}

const loadPreview = async () => {
  if (!items.value.length) {
    preview.value = {
      subtotal_amount: '0.00',
      full_reduction_amount: '0.00',
      coupon_discount_amount: '0.00',
      final_payable_amount: '0.00',
      coupon_error: ''
    }
    return
  }
  previewLoading.value = true
  try {
    const res = await couponApi.pricePreview({
      coupon_id: checkout.couponId || null
    })
    preview.value = {
      subtotal_amount: res?.subtotal_amount || totalPrice.value || '0.00',
      full_reduction_amount: res?.full_reduction_amount || '0.00',
      coupon_discount_amount: res?.coupon_discount_amount || '0.00',
      final_payable_amount: res?.final_payable_amount || totalPrice.value || '0.00',
      coupon_error: res?.coupon_error || ''
    }
  } catch (e) {
    preview.value = {
      subtotal_amount: totalPrice.value || '0.00',
      full_reduction_amount: '0.00',
      coupon_discount_amount: '0.00',
      final_payable_amount: totalPrice.value || '0.00',
      coupon_error: e?.response?.data?.error || ''
    }
  } finally {
    previewLoading.value = false
  }
}

const refreshAll = async () => {
  await Promise.all([loadAddresses(), loadCoupons(), loadCart()])
  await loadPreview()
}

const updateQty = async row => {
  try {
    await cartApi.updateQuantity(row.id, row.quantity)
    ElMessage.success('数量已更新')
    await loadCart()
    await loadPreview()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '更新失败')
  }
}

const removeItem = async row => {
  try {
    await cartApi.removeFromCart(row.id)
    ElMessage.success('已移除')
    await loadCart()
    await loadPreview()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '移除失败')
  }
}

const clearCart = async () => {
  try {
    await cartApi.clearCart()
    ElMessage.success('购物车已清空')
    await loadCart()
    await loadPreview()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '清空失败')
  }
}

const createOrder = async () => {
  checkoutLoading.value = true
  try {
    const orderRes = await orderApi.createOrder({
      address_id: checkout.addressId,
      remark: checkout.remark || ''
    })
    if (checkout.couponId) {
      await couponApi.applyCoupon(orderRes.order_id, { coupon_id: checkout.couponId })
    }
    ElMessage.success('订单已生成')
    checkout.remark = ''
    checkout.couponId = null
    router.push('/orders')
    await loadCart()
    await loadCoupons()
    await loadPreview()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '生成订单失败')
  } finally {
    checkoutLoading.value = false
  }
}

const goOrders = () => {
  router.push('/orders')
}

onMounted(refreshAll)
</script>

<style scoped>
.cart-page {
  padding: 8px;
}

.cart-card,
.checkout-card {
  border-radius: 14px;
}

.header,
.checkout-title {
  font-weight: 800;
  color: #23354d;
}

.item-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.thumb {
  width: 68px;
  height: 68px;
  object-fit: cover;
  border-radius: 8px;
  background: #f4f7fc;
}

.item-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.item-name {
  max-width: 240px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-weight: 700;
  color: #2c3a4d;
}

.item-price {
  color: #617081;
  font-size: 12px;
}

.qty-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.summary {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding-top: 14px;
  color: #59687c;
}

.total {
  font-size: 18px;
  font-weight: 800;
  color: #ff5a45;
}

.preview-box {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e7eef9;
  border-radius: 10px;
  background: #f9fbff;
}

.preview-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  color: #4b5f77;
}

.preview-row:last-child {
  margin-bottom: 0;
}

.total-row {
  padding-top: 6px;
  border-top: 1px dashed #d6e3f7;
  color: #22334b;
}

.preview-error {
  margin-top: 8px;
  color: #d03050;
  font-size: 12px;
}

@media (max-width: 992px) {
  .cart-page {
    padding: 0;
  }

  .summary {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}
</style>
