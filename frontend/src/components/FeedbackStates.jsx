import './FeedbackStates.css'

export function LoadingState({ message = 'Yükleniyor…' }) {
  return (
    <div className="feedback-state feedback-loading" role="status">
      <span aria-hidden="true" className="feedback-spinner" />
      <span>{message}</span>
    </div>
  )
}

export function ErrorState({
  message = 'Bir şeyler ters gitti.',
  onRetry,
  retrying = false,
  children,
}) {
  return (
    <section className="feedback-state feedback-error" role="alert">
      <h2>Bir şeyler ters gitti</h2>
      <p>{message}</p>
      <div className="feedback-actions">
        <button disabled={retrying} onClick={onRetry} type="button">
          {retrying ? 'Yeniden deneniyor…' : 'Tekrar dene'}
        </button>
        {children}
      </div>
    </section>
  )
}

export function EmptyState({ title, description, action }) {
  return (
    <section className="feedback-state feedback-empty">
      <h2>{title}</h2>
      <p>{description}</p>
      {action && <div className="feedback-actions">{action}</div>}
    </section>
  )
}
