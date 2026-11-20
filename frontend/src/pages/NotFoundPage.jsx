import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <section className="panel">
      <h1>Sayfa bulunamadı</h1>
      <p className="muted">Aradığın sayfa mevcut değil.</p>
      <Link className="text-link" to="/">
        Dükkânlara dön
      </Link>
    </section>
  )
}
