import { useEffect, useMemo, useState } from 'react'
import { api, clearTokens, getAccessToken, saveTokens } from '../api/client.js'
import { AuthContext } from './authContext.js'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isReady, setIsReady] = useState(() => !getAccessToken())

  useEffect(() => {
    let active = true
    const handleAuthExpired = () => {
      if (active) setUser(null)
    }

    window.addEventListener('kahvecell:auth-expired', handleAuthExpired)
    if (getAccessToken()) {
      api
        .get('/auth/me')
        .then(({ data }) => {
          if (active) setUser(data)
        })
        .catch(() => {
          clearTokens()
          if (active) setUser(null)
        })
        .finally(() => {
          if (active) setIsReady(true)
        })
    }

    return () => {
      active = false
      window.removeEventListener('kahvecell:auth-expired', handleAuthExpired)
    }
  }, [])

  const value = useMemo(
    () => ({
      user,
      isReady,
      isAuthenticated: Boolean(user),
      signIn(tokenResponse) {
        saveTokens(tokenResponse)
        setUser(tokenResponse.user)
      },
      async signOut() {
        try {
          if (getAccessToken()) await api.post('/auth/logout')
        } finally {
          clearTokens()
          setUser(null)
        }
      },
    }),
    [user, isReady],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
