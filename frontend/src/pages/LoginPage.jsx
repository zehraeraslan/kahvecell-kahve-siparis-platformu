import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client.js'
import { LoadingState } from '../components/FeedbackStates.jsx'
import { useToast } from '../context/useToast.js'
import { useAuth } from '../context/useAuth.js'

export function LoginPage() {
  const [phoneNumber, setPhoneNumber] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const formRef = useRef(null)
  const { dismissToast, notifyError, notifySuccess } = useToast()
  const { signIn } = useAuth()
  const navigate = useNavigate()

  async function login(event) {
    event.preventDefault()
    dismissToast()
    setBusy(true)
    try {
      const { data } = await api.post('/auth/login', {
        phone_number: phoneNumber,
        password,
      })
      signIn(data)
      notifySuccess('Giriş başarılı.')
      navigate(data.user.role === 'SHOP_OWNER' ? '/owner/orders' : '/')
    } catch (requestError) {
      notifyError(
        getErrorMessage(requestError, 'Telefon numarası veya şifre hatalı.'),
        () => formRef.current?.requestSubmit(),
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="auth-card">
      <Link className="auth-brand" to="/">
        <span aria-hidden="true">☕</span> KahveCell
      </Link>
      <h1>Tekrar hoş geldin</h1>
      <p className="muted">Kahve keyfine devam etmek için giriş yap.</p>
      {busy && <LoadingState message="Giriş yapılıyor…" />}
      <form className="form-stack" onSubmit={login} ref={formRef}>
        <label>
          Telefon numarası
          <input
            autoComplete="tel"
            onChange={(event) => setPhoneNumber(event.target.value)}
            placeholder="0555 000 00 00"
            required
            value={phoneNumber}
          />
        </label>
        <label>
          Şifre
          <input
            autoComplete="current-password"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </label>
        <button disabled={busy} type="submit">
          {busy ? 'Giriş yapılıyor…' : 'Giriş yap'}
        </button>
      </form>
      <p className="muted">
        Henüz hesabın yok mu? <Link to="/register">Hesap oluştur</Link>
      </p>
    </section>
  )
}
