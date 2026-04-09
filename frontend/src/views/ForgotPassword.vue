<template>
  <div class="forgot-password-page">
    <el-card class="forgot-card" shadow="never">
      <template #header>
        <div class="header">玩偶商城 - 忘记密码</div>
      </template>

      <el-alert v-if="errorMsg" class="alert" :title="errorMsg" type="error" show-icon :closable="false" />
      <el-alert v-if="successMsg" class="alert" :title="successMsg" type="success" show-icon :closable="false" />

      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px" @submit.prevent>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入注册邮箱" autocomplete="email" />
        </el-form-item>

        <el-form-item label="邮箱验证码" prop="email_code">
          <div class="email-code-row">
            <el-input v-model="form.email_code" placeholder="请输入邮箱验证码" maxlength="6" style="width: 150px" />
            <el-button type="primary" :disabled="emailCodeSending || emailCodeCountdown > 0" @click="sendEmailCode">
              {{ emailCodeCountdown > 0 ? `${emailCodeCountdown}秒后重试` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="form.new_password" type="password" placeholder="请输入新密码（至少10位，包含大小写字母和数字）" show-password @input="checkPasswordStrength" />
          <div class="password-strength" v-if="form.new_password">
            <div class="strength-bar">
              <div class="strength-fill" :class="passwordStrengthClass" :style="{ width: passwordStrengthPercent + '%' }"></div>
            </div>
            <span class="strength-text" :class="passwordStrengthClass">{{ passwordStrengthText }}</span>
          </div>
          <div class="password-tips">密码要求：长度至少10位，包含大写字母、小写字母和数字</div>
        </el-form-item>

        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="form.confirm_password" type="password" placeholder="请再次输入新密码" show-password />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="onSubmit">重置密码</el-button>
          <el-button class="link" text type="primary" @click="goLogin">返回登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { userApi } from '../api/user'

const router = useRouter()
const formRef = ref(null)

const form = reactive({
  email: '',
  email_code: '',
  new_password: '',
  confirm_password: ''
})

const loading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')
const emailCodeSending = ref(false)
const emailCodeCountdown = ref(0)
const passwordStrength = ref(0)

const checkPasswordStrength = () => {
  const pwd = form.new_password
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
    callback(new Error('请输入新密码'))
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
  if (value !== form.new_password) {
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
  email_code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为6位', trigger: 'blur' }
  ],
  new_password: [
    { validator: validatePassword, trigger: 'blur' }
  ],
  confirm_password: [
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const sendEmailCode = async () => {
  if (!form.email) {
    ElMessage.warning('请先输入邮箱')
    return
  }
  emailCodeSending.value = true
  try {
    await userApi.sendEmailCode(form.email, 'forgot')
    ElMessage.success('验证码已发送')
    emailCodeCountdown.value = 60
    const timer = setInterval(() => {
      emailCodeCountdown.value--
      if (emailCodeCountdown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (err) {
    ElMessage.error(err.message || '发送失败')
  } finally {
    emailCodeSending.value = false
  }
}

const onSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  errorMsg.value = ''
  successMsg.value = ''

  try {
    await userApi.resetPassword({
      email: form.email,
      code: form.email_code,
      password: form.new_password
    })
    ElMessage.success('密码重置成功')
    setTimeout(() => router.push('/login'), 1500)
  } catch (err) {
    errorMsg.value = err.message || '重置失败'
  } finally {
    loading.value = false
  }
}

const goLogin = () => router.push('/login')
</script>

<style scoped>
.forgot-password-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.forgot-card { width: 450px; }
.header { font-size: 20px; font-weight: bold; text-align: center; color: #303133; }
.alert { margin-bottom: 20px; }
.email-code-row { display: flex; gap: 10px; }
.password-strength { margin-top: 8px; }
.strength-bar { height: 4px; background: #ddd; border-radius: 2px; }
.strength-fill { height: 100%; transition: all 0.3s; border-radius: 2px; }
.strength-fill.weak { background: #f56c6c; }
.strength-fill.medium { background: #e6a23c; }
.strength-fill.strong { background: #67c23a; }
.strength-text { font-size: 12px; }
.strength-text.weak { color: #f56c6c; }
.strength-text.medium { color: #e6a23c; }
.strength-text.strong { color: #67c23a; }
.password-tips { font-size: 12px; color: #909399; margin-top: 4px; }
.link { margin-left: 10px; }
</style>
