<template>
  <div class="register-page">
    <el-card class="register-card" shadow="never">
      <template #header>
        <div class="header">玩偶商城 - 注册</div>
      </template>

      <el-alert
        v-if="errorMsg"
        class="alert"
        :title="errorMsg"
        type="error"
        show-icon
        :closable="false"
      />

      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" @submit.prevent>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" autocomplete="email" />
        </el-form-item>

        <el-form-item label="账号名" prop="username">
          <el-input v-model="form.username" placeholder="请输入账号名" autocomplete="username" />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码（至少10位，含大小写字母和数字）"
            show-password
            @input="checkPasswordStrength"
          />
          <div class="password-strength" v-if="form.password">
            <div class="strength-bar">
              <div
                class="strength-fill"
                :class="passwordStrengthClass"
                :style="{ width: passwordStrengthPercent + '%' }"
              ></div>
            </div>
            <span class="strength-text" :class="passwordStrengthClass">{{ passwordStrengthText }}</span>
          </div>
          <div class="password-tips">密码要求：长度≥10位，包含大写字母、小写字母、数字</div>
        </el-form-item>

        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="form.confirm_password"
            type="password"
            placeholder="请再次输入密码"
            show-password
          />
        </el-form-item>

        <el-form-item label="图片验证码" prop="captcha_code">
          <div class="captcha-row">
            <el-input
              v-model="form.captcha_code"
              placeholder="请输入验证码"
              maxlength="4"
              style="width: 150px"
            />
            <img
              v-if="captchaImage"
              :src="captchaImage"
              class="captcha-img"
              @click="refreshCaptcha"
              alt="验证码"
            />
            <el-button link type="primary" @click="refreshCaptcha">刷新</el-button>
          </div>
        </el-form-item>

        <el-form-item label="邮箱验证码" prop="email_code">
          <div class="email-code-row">
            <el-input
              v-model="form.email_code"
              placeholder="请输入邮箱验证码"
              maxlength="6"
              style="width: 150px"
            />
            <el-button
              type="primary"
              :disabled="emailCodeSending || emailCodeCountdown > 0"
              @click="sendEmailCode"
            >
              {{ emailCodeCountdown > 0 ? `${emailCodeCountdown}秒后重试` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="onRegister">注册</el-button>
          <el-button class="link" text type="primary" @click="goLogin">去登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { userApi } from '../api/user'

const router = useRouter()
const formRef = ref(null)

const form = reactive({
  email: '',
  username: '',
  password: '',
  confirm_password: '',
  captcha_id: '',
  captcha_code: '',
  email_code: ''
})

const captchaImage = ref('')
const loading = ref(false)
const errorMsg = ref('')
const emailCodeSending = ref(false)
const emailCodeCountdown = ref(0)
const passwordStrength = ref(0)

const checkPasswordStrength = () => {
  const pwd = form.password
  let strength = 0

  if (pwd.length >= 10) strength += 25
  if (pwd.length >= 12) strength += 10
  if (/[A-Z]/.test(pwd)) strength += 20
  if (/[a-z]/.test(pwd)) strength += 20
  if (/\d/.test(pwd)) strength += 20
  if (/[^A-Za-z0-9]/.test(pwd)) strength += 5

  passwordStrength.value = Math.min(strength, 100)
}

const passwordStrengthClass = computed(() => {
  if (passwordStrength.value < 40) return 'weak'
  if (passwordStrength.value < 70) return 'medium'
  return 'strong'
})

const passwordStrengthText = computed(() => {
  if (passwordStrength.value < 40) return '弱'
  if (passwordStrength.value < 70) return '中'
  return '强'
})

const passwordStrengthPercent = computed(() => passwordStrength.value)

const validatePassword = (rule, value, callback) => {
  if (!value) {
    callback(new Error('请输入密码'))
    return
  }
  if (value.length < 10) {
    callback(new Error('密码长度不能少于10位'))
    return
  }
  if (!/[A-Z]/.test(value)) {
    callback(new Error('密码必须包含大写字母'))
    return
  }
  if (!/[a-z]/.test(value)) {
    callback(new Error('密码必须包含小写字母'))
    return
  }
  if (!/\d/.test(value)) {
    callback(new Error('密码必须包含数字'))
    return
  }
  callback()
}

const validateConfirmPassword = (rule, value, callback) => {
  if (!value) {
    callback(new Error('请再次输入密码'))
    return
  }
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
    return
  }
  callback()
}

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  username: [
    { required: true, message: '请输入账号名', trigger: 'blur' },
    { min: 3, max: 20, message: '账号名长度在3-20个字符之间', trigger: 'blur' }
  ],
  password: [{ required: true, validator: validatePassword, trigger: 'blur' }],
  confirm_password: [{ required: true, validator: validateConfirmPassword, trigger: 'blur' }],
  captcha_code: [
    { required: true, message: '请输入图片验证码', trigger: 'blur' },
    { len: 4, message: '验证码为4位字符', trigger: 'blur' }
  ],
  email_code: [
    { required: true, message: '请输入邮箱验证码', trigger: 'blur' },
    { len: 6, message: '验证码为6位数字', trigger: 'blur' }
  ]
}

const refreshCaptcha = async () => {
  try {
    const res = await userApi.getCaptcha()
    form.captcha_id = res.captcha_id
    captchaImage.value = res.captcha_image
    form.captcha_code = ''
  } catch (e) {
    console.error('获取验证码失败', e)
  }
}

const sendEmailCode = async () => {
  if (!form.email) {
    ElMessage.warning('请先输入邮箱')
    return
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(form.email)) {
    ElMessage.warning('邮箱格式不正确')
    return
  }

  emailCodeSending.value = true
  try {
    const res = await userApi.sendEmailCode(form.email, 'register')
    ElMessage.success(res?.message || '验证码已发送，请注意查收邮箱')

    emailCodeCountdown.value = 60
    const timer = setInterval(() => {
      emailCodeCountdown.value--
      if (emailCodeCountdown.value <= 0) {
        clearInterval(timer)
      }
    }, 1000)
  } catch (err) {
    ElMessage.error(err?.response?.data?.error || '发送失败')
  } finally {
    emailCodeSending.value = false
  }
}

const extractErrorMessage = err => {
  const data = err?.response?.data
  if (!data) return err?.message || '注册失败'
  if (typeof data === 'string') return data
  if (typeof data.error === 'string') return data.error
  const firstKey = Object.keys(data)[0]
  const firstVal = firstKey ? data[firstKey] : null
  if (Array.isArray(firstVal) && firstVal.length) return String(firstVal[0])
  if (typeof firstVal === 'string') return firstVal
  return '注册失败'
}

const onRegister = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  errorMsg.value = ''

  try {
    await userApi.register({
      email: form.email,
      username: form.username,
      password: form.password,
      confirm_password: form.confirm_password,
      captcha_id: form.captcha_id,
      captcha_code: form.captcha_code,
      email_code: form.email_code
    })

    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (err) {
    errorMsg.value = extractErrorMessage(err)
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}

const goLogin = () => {
  router.push('/login')
}

onMounted(() => {
  refreshCaptcha()
})
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  padding: 24px;
}

.register-card {
  width: 520px;
}

.header {
  font-weight: 600;
}

.alert {
  margin-bottom: 16px;
}

.captcha-row,
.email-code-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.captcha-img {
  height: 40px;
  cursor: pointer;
  border-radius: 4px;
  border: 1px solid #dcdfe6;
}

.link {
  margin-left: 12px;
}

.password-strength {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.strength-bar {
  width: 150px;
  height: 6px;
  background: #e4e7ed;
  border-radius: 3px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  transition: all 0.3s;
}

.strength-fill.weak {
  background: #f56c6c;
}

.strength-fill.medium {
  background: #e6a23c;
}

.strength-fill.strong {
  background: #67c23a;
}

.strength-text {
  font-size: 12px;
  font-weight: 500;
}

.strength-text.weak {
  color: #f56c6c;
}

.strength-text.medium {
  color: #e6a23c;
}

.strength-text.strong {
  color: #67c23a;
}

.password-tips {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
