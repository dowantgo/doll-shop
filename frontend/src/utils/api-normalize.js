export function normalizeList(data) {
  if (Array.isArray(data)) {
    return data
  }
  if (data && typeof data === 'object' && 'results' in data) {
    return data.results
  }
  return []
}

export function normalizePaginated(data) {
  if (!data || typeof data !== 'object') {
    return { results: [], count: 0 }
  }
  if (Array.isArray(data)) {
    return { results: data, count: data.length }
  }
  return {
    results: Array.isArray(data.results) ? data.results : [],
    count: typeof data.count === 'number' ? data.count : 0
  }
}
