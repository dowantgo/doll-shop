import request from '../utils/request'

const toStringValue = value => {
  if (value === null || value === undefined) return ''
  return String(value).trim()
}

const toArrayValue = value => {
  if (Array.isArray(value)) return value
  if (value === null || value === undefined || value === '') return []
  return [value]
}

const extractPayload = response => {
  if (response && typeof response === 'object' && 'data' in response && response.data && typeof response.data === 'object') {
    return response.data
  }
  return response && typeof response === 'object' ? response : {}
}

export const reviewApi = {
  normalizePagedResponse(data) {
    return {
      count: Number(data?.count || 0),
      next: data?.next || null,
      previous: data?.previous || null,
      results: Array.isArray(data?.results) ? data.results : []
    }
  },

  getProductReviews(productId, params) {
    return request
      .get(`/reviews/product/${productId}/`, { params })
      .then(data => this.normalizePagedResponse(data))
  },

  createProductReview(productId, data) {
    return request.post(`/reviews/product/${productId}/`, data)
  },

  createReviewReply(reviewId, data) {
    return request.post(`/reviews/${reviewId}/reply/`, data)
  },

  getMyReviews(params) {
    return request.get('/reviews/my/', { params }).then(data => this.normalizePagedResponse(data))
  },

  extractSubmissionFeedback(response) {
    const payload = extractPayload(response)
    const hitSensitiveWords = toArrayValue(
      payload.hit_sensitive_words || payload.sensitive_words || payload.blocked_words || payload.hit_words
    )
      .map(item => toStringValue(item))
      .filter(Boolean)
    const sanitizedContent = toStringValue(payload.sanitized_content || payload.cleaned_content || payload.safe_content)
    const suggestion = toStringValue(payload.suggestion || payload.tip || payload.hint)
    const message = toStringValue(payload.message || payload.error || payload.detail)

    return {
      hitSensitiveWords,
      sanitizedContent,
      suggestion,
      message,
      hasFeedback: hitSensitiveWords.length > 0 || Boolean(sanitizedContent) || Boolean(suggestion)
    }
  }
}
