<template>
  <el-dialog
    v-model="visible"
    title="支付"
    width="460px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div v-if="step === 'select'" class="pay-step">
      <p class="pay-amount">订单金额：¥{{ amount }}</p>
      <el-radio-group v-model="selectedMethod">
        <el-radio-button label="mock">模拟支付</el-radio-button>
        <el-radio-button label="alipay">支付宝</el-radio-button>
      </el-radio-group>
      <div class="pay-actions">
        <el-button type="primary" :loading="loading" @click="createPayment">创建支付</el-button>
      </div>
    </div>

    <div v-else-if="step === 'qrcode'" class="pay-step">
      <p>支付方式：{{ selectedMethod }}</p>
      <p>支付单号：{{ paymentId }}</p>

      <div v-if="qrCodeImage" class="qrcode-box">
        <p class="qrcode-title">请扫码支付</p>
        <img :src="qrCodeImage" alt="支付二维码" class="qrcode-img" />
      </div>

      <p class="qrcode-link-title">二维码链接（备用）：</p>
      <el-input type="textarea" :model-value="qrCodeUrl" :rows="2" readonly />

      <div class="pay-actions">
        <el-button v-if="selectedMethod === 'mock'" type="success" :loading="mockLoading" @click="mockPay">
          模拟支付成功
        </el-button>
        <el-button @click="handleClose">取消支付</el-button>
      </div>
    </div>

    <div v-else-if="step === 'success'" class="pay-step">
      <p>支付成功</p>
      <el-button type="primary" @click="handleSuccess">完成</el-button>
    </div>

    <div v-else class="pay-step">
      <p>支付失败</p>
      <p class="fail-reason">{{ failReason }}</p>
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

<style scoped>
.pay-step {
  display: grid;
  gap: 10px;
}

.pay-amount {
  font-weight: 700;
  color: #22364f;
}

.qrcode-box {
  text-align: center;
  margin: 14px 0;
  padding: 12px;
  border: 1px dashed #d9e4f2;
  border-radius: 10px;
  background: #f8fbff;
}

.qrcode-title {
  margin-bottom: 8px;
  color: #5f6b7a;
}

.qrcode-img {
  max-width: 220px;
  max-height: 220px;
  border: 1px solid #e6edf7;
  border-radius: 8px;
  background: #fff;
}

.qrcode-link-title {
  margin-top: 8px;
  color: #5f6b7a;
}

.fail-reason {
  color: #f56c6c;
  word-break: break-all;
}

.pay-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}
</style>
