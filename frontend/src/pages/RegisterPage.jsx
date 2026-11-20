import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client.js'
import { LoadingState } from '../components/FeedbackStates.jsx'
import { useToast } from '../context/useToast.js'
import { useAuth } from '../context/useAuth.js'

export function RegisterPage() {
  const [phoneNumber, setPhoneNumber] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [step, setStep] = useState('phone')
  const [busy, setBusy] = useState(false)
  const formRef = useRef(null)
  const { dismissToast, notifyError, notifySuccess } = useToast()
  const { signIn } = useAuth()
  const navigate = useNavigate()

  async function register(event) {
    event.preventDefault()
    dismissToast()
    setBusy(true)
    try {
      const { data } = await api.post('/auth/register', {
        phone_number: phoneNumber,
        full_name: fullName,
        password,
      })
      setPhoneNumber(data.phone_number)
      setStep('otp')
      notifySuccess('Kayıt başlatıldı. Telefon doğrulaması bekleniyor.')
    } catch (requestError) {
      notifyError(
        getErrorMessage(requestError, 'Kayıt başlatılamadı.'),
        () => formRef.current?.requestSubmit(),
      )
    } finally {
      setBusy(false)
    }
  }

  async function verifyCode(event) {
    event.preventDefault()
    dismissToast()
    setBusy(true)
    try {
      const { data } = await api.post('/auth/verify-otp', {
        phone_number: phoneNumber,
        code,
      })
      signIn(data)
      notifySuccess('Telefon doğrulandı. KahveCell’e hoş geldin!')
      navigate('/')
    } catch (requestError) {
      notifyError(
        getErrorMessage(requestError, 'Kod doğrulanamadı.'),
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
      <h1>Aramıza katıl</h1>
      <p className="muted">KahveCell hesabını birkaç adımda oluştur.</p>
      {busy && (
        <LoadingState
          message={
            step === 'phone'
              ? 'Hesap oluşturuluyor…'
              : 'Kod kontrol ediliyor…'
          }
        />
      )}
      {step === 'phone' ? (
        <form className="form-stack" onSubmit={register} ref={formRef}>
          <label>
            Ad soyad
            <input
              autoComplete="name"
              onChange={(event) => setFullName(event.target.value)}
              required
              value={fullName}
            />
          </label>
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
              autoComplete="new-password"
              minLength={8}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
          <button disabled={busy} type="submit">
            {busy ? 'Hesap oluşturuluyor…' : 'Hesap oluştur'}
          </button>
        </form>
      ) : (
        <form className="form-stack" onSubmit={verifyCode} ref={formRef}>
          <p className="notice">
            Telefonuna gelen 4 haneli kodu gir. Test için kod her zaman <strong>1234</strong>.
          </p>
          <label>
            Doğrulama kodu
            <input
              autoComplete="one-time-code"
              inputMode="numeric"
              maxLength={4}
              onChange={(event) => setCode(event.target.value)}
              required
              value={code}
            />
          </label>
          <div className="form-actions">
            <button disabled={busy} type="submit">
              {busy ? 'Kontrol ediliyor…' : 'Telefonu doğrula'}
            </button>
            <button
              className="button-secondary"
              onClick={() => setStep('phone')}
              type="button"
            >
              Geri
            </button>
          </div>
        </form>
      )}
      <p className="muted">
        Zaten hesabın var mı? <Link to="/login">Giriş yap</Link>
      </p>
    </section>
  )
}
