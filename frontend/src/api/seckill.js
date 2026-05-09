import request from '../utils/request'

const SECKILL_ACTIVITY_STATUS_TEXT = {
  draft: '草稿',
  preheating: '预热中',
  online: '进行中',
  ended: '已结束',
  offline: '已下线'
}

const SECKILL_ACTIVITY_STATUS_TYPE = {
  draft: 'info',
  preheating: 'warning',
  online: 'success',
  ended: 'danger',
  offline: 'info'
}

const SECKILL_RESERVATION_STATUS_TEXT = {
  reserved: '预占中',
  ordered: '已下单',
  paid: '已支付',
  cancelled: '已取消',
  expired: '已过期'
}

const SECKILL_RESERVATION_STATUS_TYPE = {
  reserved: 'warning',
  ordered: 'primary',
  paid: 'success',
  cancelled: 'info',
  expired: 'danger'
}

const normalizeText = value => {
  if (value === null || value === undefined) return ''
  return String(value).trim()
}

const readErrorMessage = error => {
  const data = error?.response?.data
  const candidates = [
    data?.error,
    data?.message,
    data?.detail,
    data?.msg,
    Array.isArray(data?.non_field_errors) ? data.non_field_errors[0] : '',
    error?.message
  ]
  return normalizeText(candidates.find(Boolean))
}

const LOCALIZED_ERROR_RULES = [
  {
    match: /per-user|limit|限购|每人|单用户|user limit/i,
    message: '已超过每人限购数量，请减少购买件数后再试'
  },
  {
    match: /stock|库存|sold out|out of stock|不足/i,
    message: '秒杀库存不足，请选择其他商品或稍后再试'
  },
  {
    match: /activity|活动.*(ended|结束|下线|未开始|预热|进行中)|status/i,
    message: '当前秒杀活动状态不可用，请稍后再试'
  },
  {
    match: /expired|过期|超时/i,
    message: '秒杀预占已过期，请重新发起秒杀'
  },
  {
    match: /paid|已支付/i,
    message: '当前秒杀订单已支付完成，无需重复提交'
  },
  {
    match: /address|收货地址/i,
    message: '收货地址信息不完整，请先选择可用地址'
  },
  {
    match: /submit token|令牌|token/i,
    message: '秒杀令牌已失效，请重新发起秒杀'
  },
  {
    match: /processing|处理中/i,
    message: '当前秒杀订单正在处理中，请稍后刷新结果'
  },
  {
    match: /rate|frequent|429|too many/i,
    message: '当前秒杀请求过于频繁，请稍后再试'
  }
]

export const seckillApi = {
  listActivities() {
    return request.get('/seckill/activities/')
  },

  getProductActiveActivity(productId) {
    return request.get(`/seckill/product/${productId}/active/`)
  },

  issueSubmitToken(activityId) {
    return request.post('/seckill/issue-submit-token/', { activity_id: activityId })
  },

  preReserve(data, idempotencyKey) {
    const headers = {}
    if (idempotencyKey) headers['X-Idempotency-Key'] = idempotencyKey
    return request.post('/seckill/pre-reserve/', data, { headers })
  },

  createOrder(data) {
    return request.post('/seckill/create-order/', data)
  },

  getMyReservations() {
    return request.get('/seckill/my-reservations/')
  },

  cancelReservation(reservationId) {
    return request.post(`/seckill/reservations/${reservationId}/cancel/`)
  },

  formatActivityStatus(status) {
    const key = normalizeText(status)
    return SECKILL_ACTIVITY_STATUS_TEXT[key] || key || '未知状态'
  },

  formatActivityStatusType(status) {
    const key = normalizeText(status)
    return SECKILL_ACTIVITY_STATUS_TYPE[key] || 'info'
  },

  formatReservationStatus(status) {
    const key = normalizeText(status)
    return SECKILL_RESERVATION_STATUS_TEXT[key] || key || '未知状态'
  },

  formatReservationStatusType(status) {
    const key = normalizeText(status)
    return SECKILL_RESERVATION_STATUS_TYPE[key] || 'info'
  },

  normalizeSeckillError(error, fallback = '秒杀操作失败') {
    const rawMessage = readErrorMessage(error) || fallback
    const matchedRule = LOCALIZED_ERROR_RULES.find(rule => rule.match.test(rawMessage))
    return matchedRule?.message || rawMessage || fallback
  }
}
