import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { ToastNotice } from '../components/ToastNotice.jsx'
import { ToastContext } from './toastContext.js'

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null)
  const nextId = useRef(0)

  const dismissToast = useCallback(() => setToast(null), [])

  const notifySuccess = useCallback((message) => {
    setToast({ id: ++nextId.current, message, type: 'success' })
  }, [])

  const notifyError = useCallback((message, onRetry) => {
    setToast({ id: ++nextId.current, message, onRetry, type: 'error' })
  }, [])

  useEffect(() => {
    if (!toast || toast.type !== 'success') return undefined

    const timer = setTimeout(() => setToast(null), 5000)
    return () => clearTimeout(timer)
  }, [toast])

  const value = useMemo(
    () => ({ dismissToast, notifyError, notifySuccess }),
    [dismissToast, notifyError, notifySuccess],
  )

  function retryToast() {
    const retry = toast?.onRetry
    dismissToast()
    retry?.()
  }

  return (
    <ToastContext.Provider value={value}>
      {children}
      {toast && (
        <ToastNotice
          key={toast.id}
          message={toast.message}
          onDismiss={dismissToast}
          onRetry={toast.onRetry ? retryToast : undefined}
          type={toast.type}
        />
      )}
    </ToastContext.Provider>
  )
}
