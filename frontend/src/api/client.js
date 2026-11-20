import axios from 'axios'

const ACCESS_TOKEN_KEY = 'kahvecell.accessToken'
const REFRESH_TOKEN_KEY = 'kahvecell.refreshToken'
const AUTH_EXPIRED_EVENT = 'kahvecell:auth-expired'

export const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1',
  timeout: 10000,
})

export function saveTokens({ access_token, refresh_token }) {
  localStorage.setItem(ACCESS_TOKEN_KEY, access_token)
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token)
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshRequest

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const request = error.config
    const isAuthFlow = [
      '/auth/login',
      '/auth/register',
      '/auth/verify-otp',
      '/auth/refresh',
      '/auth/logout',
    ].some((path) => request?.url?.includes(path))

    if (
      error.response?.status !== 401 ||
      !request ||
      request._retried ||
      isAuthFlow
    ) {
      return Promise.reject(error)
    }

    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
    if (!refreshToken) {
      clearTokens()
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
      return Promise.reject(error)
    }

    request._retried = true
    try {
      refreshRequest ??= api
        .post('/auth/refresh', { refresh_token: refreshToken })
        .then(({ data }) => {
          saveTokens(data)
          return data.access_token
        })
        .finally(() => {
          refreshRequest = null
        })

      const newAccessToken = await refreshRequest
      request.headers.Authorization = `Bearer ${newAccessToken}`
      return api(request)
    } catch (refreshError) {
      clearTokens()
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
      return Promise.reject(refreshError)
    }
  },
)

export function getErrorMessage(error, fallback = 'Bir hata oluştu.') {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join(', ')
  }
  return fallback
}
