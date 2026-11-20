import '../context/Toast.css'

export function ToastNotice({ type, message, onRetry, onDismiss }) {
  function retry() {
    onDismiss?.()
    onRetry?.()
  }

  return (
    <aside
      aria-live={type === 'error' ? 'assertive' : 'polite'}
      className={`toast is-${type}`}
      role={type === 'error' ? 'alert' : 'status'}
    >
      <p>{message}</p>
      <div className="toast-actions">
        {onRetry && (
          <button className="toast-retry" onClick={retry} type="button">
            Tekrar dene
          </button>
        )}
        {onDismiss && (
          <button
            aria-label="Bildirimi kapat"
            className="toast-dismiss"
            onClick={onDismiss}
            type="button"
          >
            ×
          </button>
        )}
      </div>
    </aside>
  )
}
