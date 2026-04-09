<template>
  <el-dialog
    v-model="visible"
    title="支付"
    width="440px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div v-if="step === 'select'">
      <p>订单金额：￥{{ amount }}</p>
      <el-radio-group v-model="selectedMethod">
        <el-radio-button label="mock">模拟支付</el-radio-button>
        <el-radio-button label="alipay">支付宝</el-radio-button>
      </el-radio-group>
      <div style="margin-top: 16px">
        <el-button type="primary" :loading="loading" @click="createPayment">创建支付</el-button>
      </div>
    </div>

    <div v-else-if="step === 'qrcode'">
      <p>支付方式：{{ selectedMethod }}</p>
      <p>支付单号：{{ paymentId }}</p>
      
      <!-- 二维码图片展示 -->
      <div v-if="qrCodeImage" style="text-align: center; margin: 16px 0;">
        <p style="margin-bottom: 8px;">请扫码支付：</p>
        <img 
          :src="qrCodeImage" 
          alt="支付二维码" 
          style="max-width: 200px; max-height: 200px; border: 1px solid #eee;"
        />
      </div>
      
      <!-- 二维码链接（备用） -->
      <p style="margin-top: 16px;">二维码链接：</p>
      <el-input type="textarea" :model-value="qrCodeUrl" :rows="2" readonly />
      
      <div style="margin-top: 12px">
        <el-button v-if="selectedMethod === 'mock'" type="success" :loading="mockLoading" @click="mockPay">
          模拟支付成功
        </el-button>
        <el-button @click="handleClose">取消支付</el-button>
      </div>
    </div>

    <div v-else-if="step === 'success'">
      <p>支付成功</p>
      <el-button type="primary" @click="handleSuccess">完成</el-button>
    </div>

    <div v-else>
      <p>支付失败</p>
      <p style="color: #f56c6c; word-break: break-all">{{ failReason }}</p>
      <el-button type="primary" @click="resetState">重试</el-button>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { paymentApi } from '../api/payment'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  orderId: { type: String, default: '' },
  amount: { type: [String, Number], default: '0.00' }
})

const emit = defineEmits(['update:modelValue', 'success', 'close'])

const visible = computed({
  get: () => props.modelValue,
  set: val => emit('update:modelValue', val)
})

const step = ref('select')
const loading = ref(false)
const mockLoading = ref(false)
const selectedMethod = ref('mock')
const paymentId = ref('')
const qrCodeUrl = ref('')
const qrCodeImage = ref('')
const failReason = ref('')
let pollTimer = null

const errorText = e =>
  e?.response?.data?.error ||
  e?.response?.data?.detail ||
  e?.message ||
  '创建支付失败'

const resetState = () => {
  step.value = 'select'
  loading.value = false
  mockLoading.value = false
  selectedMethod.value = 'mock'
  paymentId.value = ''
  qrCodeUrl.value = ''
  qrCodeImage.value = ''
  failReason.value = ''
}

const clearPoll = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

watch(
  () => visible.value,
  val => {
    if (val) resetState()
    else clearPoll()
  }
)

const createPayment = async () => {
  if (!props.orderId) {
    ElMessage.error('订单号不能为空')
    return
  }

  loading.value = true
  try {
    const res = await paymentApi.createPayment(props.orderId, selectedMethod.value)
    paymentId.value = res.payment_id
    qrCodeUrl.value = res.qr_code || ''
    qrCodeImage.value = res.qr_code_image || ''
    step.value = 'qrcode'
    startPolling()
  } catch (e) {
    failReason.value = errorText(e)
    step.value = 'failed'
    ElMessage.error(failReason.value)
  } finally {
    loading.value = false
  }
}

const startPolling = () => {
  clearPoll()
  pollTimer = setInterval(async () => {
    try {
      const res = await paymentApi.getStatus(paymentId.value)
      if (res.status === 'success') {
        clearPoll()
        step.value = 'success'
      } else if (res.status === 'failed' || res.status === 'closed') {
        clearPoll()
        failReason.value = res.status === 'closed' ? '支付已关闭或超时' : '支付失败'
        step.value = 'failed'
      }
    } catch (_e) {
      // keep polling silently
    }
  }, 3000)
}

const mockPay = async () => {
  mockLoading.value = true
  try {
    await paymentApi.mockPay(paymentId.value)
    clearPoll()
    step.value = 'success'
  } catch (e) {
    ElMessage.error(errorText(e))
  } finally {
    mockLoading.value = false
  }
}

const handleSuccess = () => {
  emit('success')
  visible.value = false
}

const handleClose = async () => {
  clearPoll()
  if (paymentId.value && step.value === 'qrcode') {
    try {
      await paymentApi.closePayment(paymentId.value)
    } catch (_e) {
      // ignore close error
    }
  }
  emit('close')
  visible.value = false
}

onUnmounted(clearPoll)
</script>

