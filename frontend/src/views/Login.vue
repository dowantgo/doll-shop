<template>
  <div class="login-page">
    <el-card class="login-card" shadow="never">
      <template #header>
        <div class="header">玩偶商城 - 登录</div>
      </template>

      <el-alert
        v-if="errorMsg"
        class="alert"
        :title="errorMsg"
        type="error"
        show-icon
        :closable="false"
      />

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        @submit.prevent
      >
        <el-form-item label="用户名/邮箱" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名或邮箱"
            autocomplete="username"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            placeholder="请输入密码"
            type="password"
            autocomplete="current-password"
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

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="onLogin">登录</el-button>
          <el-button class="link" text type="primary" @click="goRegister">去注册</el-button>
          <el-button class="link" text type="info" @click="goForgotPassword">忘记密码？</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { userApi } from '../api/user'
import { useUserStore } from '../stores/userStore'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)

const form = reactive({
  username: '',
  password: '',
  captcha_id: '',
  captcha_code: ''
})

const captchaImage = ref('')
const loading = ref(false)
const errorMsg = ref('')

const rules = {
  username: [{ required: true, message: '请输入用户名或邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  captcha_code: [{ required: true, message: '请输入验证码', trigger: 'blur' }]
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

const extractErrorMessage = err => {
  const data = err?.response?.data
  if (!data) return err?.message || '登录失败'
  if (typeof data === 'string') return data
  if (typeof data.error === 'string') return data.error
  const firstKey = Object.keys(data)[0]
  const firstVal = firstKey ? data[firstKey] : null
  if (Array.isArray(firstVal) && firstVal.length) return String(firstVal[0])
  if (typeof firstVal === 'string') return firstVal
  return err?.message || '登录失败'
}

const onLogin = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  errorMsg.value = ''

  try {
    const data = await userApi.login({
      username: form.username,
      password: form.password,
      captcha_id: form.captcha_id,
      captcha_code: form.captcha_code
    })

    if (!data?.token || !data?.user) {
      throw new Error('登录返回格式异常，缺少 token 或 user')
    }

    userStore.setUser(data.user, data.token)
    ElMessage.success('登录成功')
    if (data.user.role === 'admin') {
      router.push('/admin')
    } else {
      router.push('/')
    }
  } catch (err) {
    errorMsg.value = extractErrorMessage(err)
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}

const goRegister = () => {
  router.push('/register')
}

const goForgotPassword = () => {
  router.push('/forgot-password')
}

onMounted(() => {
  refreshCaptcha()
})
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  padding: 24px;
}

.login-card {
  width: 480px;
}

.header {
  font-weight: 600;
}

.alert {
  margin-bottom: 16px;
}

.captcha-row {
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
</style>
