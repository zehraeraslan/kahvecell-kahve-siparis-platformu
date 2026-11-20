import { useEffect, useRef, useState } from 'react'
import { api, getErrorMessage } from '../api/client.js'
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from '../components/FeedbackStates.jsx'
import { ToastNotice } from '../components/ToastNotice.jsx'
import { useToast } from '../context/useToast.js'
import './SubscriptionPage.css'

const TEST_SUCCESS_CARD = '4242-4242-4242-4242'

function formatDate(value) {
  if (!value) return 'Bilgi bulunmuyor'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat('tr-TR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

export function SubscriptionPage() {
  const [plans, setPlans] = useState([])
  const [subscription, setSubscription] = useState(null)
  const [purchasePlan, setPurchasePlan] = useState(null)
  const [pendingTransaction, setPendingTransaction] = useState(null)
  const [cardNumber, setCardNumber] = useState(TEST_SUCCESS_CARD)
  const [paymentError, setPaymentError] = useState('')
  const [loadError, setLoadError] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)
  const dialogRef = useRef(null)
  const { dismissToast, notifyError, notifySuccess } = useToast()

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const [planResponse, subscriptionResponse] = await Promise.all([
          api.get('/subscriptions/plans'),
          api.get('/subscriptions/me').catch((requestError) => {
            if (requestError.response?.status === 404) return { data: null }
            throw requestError
          }),
        ])
        if (!active) return
        setPlans(planResponse.data)
        setSubscription(subscriptionResponse.data)
      } catch (requestError) {
        if (active) {
          setLoadError(
            getErrorMessage(requestError, 'Abonelik bilgileri yüklenemedi.'),
          )
        }
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => {
      active = false
    }
  }, [reloadKey])

  function retryLoad() {
    setLoading(true)
    setLoadError('')
    setReloadKey((key) => key + 1)
  }

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    if (purchasePlan && !dialog.open) dialog.showModal()
    if (!purchasePlan && dialog.open) dialog.close()
  }, [purchasePlan])

  function openPurchase(plan) {
    dismissToast()
    setPaymentError('')
    if (pendingTransaction?.planType !== plan.plan_type) {
      setPendingTransaction(null)
    }
    setCardNumber(TEST_SUCCESS_CARD)
    setPurchasePlan(plan)
  }

  function closePurchase() {
    if (busy) return
    setPaymentError('')
    setPurchasePlan(null)
  }

  async function processPayment() {
    if (!purchasePlan) return

    dismissToast()
    setPaymentError('')
    setBusy(true)
    try {
      let transactionId =
        pendingTransaction?.planType === purchasePlan.plan_type
          ? pendingTransaction.transactionId
          : null

      if (!transactionId) {
        const { data: payment } = await api.post('/payments/process', {
          plan_type: purchasePlan.plan_type,
          card_number: cardNumber,
        })
        if (!payment.success) {
          setPaymentError(payment.message || 'Ödeme başarısız oldu.')
          return
        }
        transactionId = payment.transaction_id
        setPendingTransaction({
          planType: purchasePlan.plan_type,
          transactionId,
        })
      }

      const request = subscription
        ? api.patch('/subscriptions/me', {
            plan_type: purchasePlan.plan_type,
            transaction_id: transactionId,
          })
        : api.post('/subscriptions', {
            transaction_id: transactionId,
          })
      const { data } = await request
      setSubscription(data)
      setPendingTransaction(null)
      notifySuccess(
        `${data.plan_name} aboneliğiniz başarıyla etkinleştirildi. Kalan kahve hakkı: ${
          data.remaining_credits === -1 ? 'Sınırsız' : data.remaining_credits
        }.`,
      )
      setPurchasePlan(null)
    } catch (requestError) {
      setPaymentError(
        getErrorMessage(requestError, 'Abonelik işlemi tamamlanamadı.'),
      )
    } finally {
      setBusy(false)
    }
  }

  function submitPayment(event) {
    event.preventDefault()
    processPayment()
  }

  async function cancelSubscription() {
    dismissToast()
    setBusy(true)
    try {
      await api.delete('/subscriptions/me')
      setSubscription(null)
      notifySuccess('Aboneliğiniz iptal edildi.')
    } catch (requestError) {
      notifyError(
        getErrorMessage(requestError, 'Abonelik iptal edilemedi.'),
        cancelSubscription,
      )
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <LoadingState message="Abonelik bilgileri yükleniyor…" />
  if (loadError) {
    return (
      <ErrorState
        message={loadError}
        onRetry={retryLoad}
        retrying={loading}
      />
    )
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Abonelik</h1>
          <p className="muted">
            Kahve hakkını sana uygun paketle yenile.
          </p>
        </div>
      </div>

      <section className="panel current-plan" aria-live="polite">
        {subscription ? (
          <>
            <h2>Aktif aboneliğiniz: {subscription.plan_name}</h2>
            <div className="subscription-details">
              <p>
                <span className="muted">Kalan kredi</span>
                <strong>
                  {subscription.remaining_credits === -1
                    ? 'Sınırsız'
                    : subscription.remaining_credits}
                </strong>
              </p>
              <p>
                <span className="muted">Bitiş tarihi</span>
                <strong>{formatDate(subscription.expires_at)}</strong>
              </p>
            </div>
            <button
              className="button-secondary"
              disabled={busy}
              onClick={cancelSubscription}
              type="button"
            >
              İptal Et
            </button>
          </>
        ) : (
          <h2>Aktif aboneliğiniz yok</h2>
        )}
      </section>

      {plans.length === 0 ? (
        <EmptyState
          action={
            <button onClick={retryLoad} type="button">
              Paketleri yeniden yükle
            </button>
          }
          description="Bir süre sonra tekrar deneyebilir veya sayfayı yenileyebilirsin."
          title="Paket bulunamadı"
        />
      ) : (
        <section className="plan-grid" aria-label="Abonelik paketleri">
          {plans.map((plan) => {
            const isCurrent = subscription?.plan_type === plan.plan_type
            return (
              <article
                className={`plan-card${isCurrent ? ' is-current' : ''}`}
                key={plan.plan_type}
              >
                {isCurrent && (
                  <span className="subscription-current-badge">
                    Aktif paket
                  </span>
                )}
                <h2>{plan.name}</h2>
                <p className="subscription-price">
                  <strong>{plan.monthly_price_tl.toFixed(2)} TL</strong> / ay
                </p>
                <ul>
                  <li>
                    {plan.monthly_credits == null
                      ? 'Sınırsız kahve'
                      : `${plan.monthly_credits} kahve / ay`}
                  </li>
                  <li>{plan.guest_rights} misafir hakkı</li>
                  <li>
                    {plan.priority_service
                      ? 'Öncelikli servis'
                      : 'Standart servis'}
                  </li>
                </ul>
                <button
                  disabled={busy || isCurrent}
                  onClick={() => openPurchase(plan)}
                  type="button"
                >
                  Satın Al
                </button>
              </article>
            )
          })}
        </section>
      )}

      <dialog
        aria-labelledby="subscription-payment-title"
        className="subscription-dialog"
        onCancel={closePurchase}
        onClose={() => {
          setPurchasePlan(null)
          setPaymentError('')
        }}
        onClick={(event) => {
          if (event.target === event.currentTarget) closePurchase()
        }}
        ref={dialogRef}
      >
        {purchasePlan && (
          <>
            <div className="subscription-dialog-header">
              <div>
                <h2 id="subscription-payment-title">
                  {purchasePlan.name} paketi
                </h2>
                <p className="muted">
                  {purchasePlan.monthly_price_tl.toFixed(2)} TL / ay
                </p>
              </div>
              <button
                aria-label="Ödeme penceresini kapat"
                className="button-secondary subscription-dialog-close"
                disabled={busy}
                onClick={closePurchase}
                type="button"
              >
                ×
              </button>
            </div>
            <form className="form-stack" onSubmit={submitPayment}>
              <label>
                Kart numarası
                <input
                  autoComplete="cc-number"
                  autoFocus
                  inputMode="numeric"
                  maxLength={23}
                  minLength={16}
                  onChange={(event) => setCardNumber(event.target.value)}
                  required
                  value={cardNumber}
                />
              </label>
              <p className="muted subscription-card-note">
                Test kartı, değiştirmeyin.
              </p>
              <p className="muted subscription-failure-note">
                Başarısız ödeme testi: 4000-0000-0000-0002
              </p>
              {paymentError && (
                <ToastNotice
                  message={paymentError}
                  onDismiss={() => setPaymentError('')}
                  onRetry={processPayment}
                  type="error"
                />
              )}
              <div className="subscription-dialog-actions">
                <button
                  className="button-secondary"
                  disabled={busy}
                  onClick={closePurchase}
                  type="button"
                >
                  Vazgeç
                </button>
                <button disabled={busy} type="submit">
                  {busy ? 'Ödeme yapılıyor…' : 'Onayla'}
                </button>
              </div>
            </form>
          </>
        )}
      </dialog>
    </>
  )
}
