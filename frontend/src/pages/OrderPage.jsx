import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client.js'
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from '../components/FeedbackStates.jsx'
import { useToast } from '../context/useToast.js'
import './OrderPage.css'

export function OrderPage() {
  const [searchParams] = useSearchParams()
  const shopId = searchParams.get('shopId')
  const requestedProductId = searchParams.get('productId')
  const [shop, setShop] = useState(null)
  const [subscription, setSubscription] = useState(null)
  const [productId, setProductId] = useState('')
  const [size, setSize] = useState('M')
  const [sugarLevel, setSugarLevel] = useState('0')
  const [milkPreference, setMilkPreference] = useState('WHOLE')
  const [extraShots, setExtraShots] = useState('0')
  const [loadError, setLoadError] = useState('')
  const [shopNotFound, setShopNotFound] = useState(false)
  const [loading, setLoading] = useState(Boolean(shopId))
  const [busy, setBusy] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const [loadedRequestKey, setLoadedRequestKey] = useState('')
  const { dismissToast, notifyError } = useToast()
  const navigate = useNavigate()
  const requestKey = `${shopId || ''}:${requestedProductId || ''}:${reloadKey}`

  useEffect(() => {
    if (!shopId) return undefined

    let active = true
    async function loadOrderOptions() {
      try {
        const [shopResponse, subscriptionResponse] = await Promise.all([
          api.get(`/shops/${shopId}`),
          api.get('/subscriptions/me').catch((requestError) => {
            if (requestError.response?.status === 404) return { data: null }
            throw requestError
          }),
        ])
        if (!active) return

        setShop(shopResponse.data)
        setSubscription(subscriptionResponse.data)
        setShopNotFound(false)
        const selectedProduct =
          shopResponse.data.menu.find(
            (product) => String(product.id) === requestedProductId,
          ) || shopResponse.data.menu[0]
        setProductId(selectedProduct ? String(selectedProduct.id) : '')
        setLoadError('')
      } catch (requestError) {
        if (active) {
          setShop(null)
          if (requestError.response?.status === 404) {
            setShopNotFound(true)
            setLoadError('')
          } else {
            setShopNotFound(false)
            setLoadError(
              getErrorMessage(requestError, 'Sipariş bilgileri yüklenemedi.'),
            )
          }
        }
      } finally {
        if (active) {
          setLoadedRequestKey(requestKey)
          setLoading(false)
        }
      }
    }

    loadOrderOptions()
    return () => {
      active = false
    }
  }, [reloadKey, requestedProductId, requestKey, shopId])

  function retryLoad() {
    setLoading(true)
    setLoadError('')
    setShopNotFound(false)
    setReloadKey((key) => key + 1)
  }

  const selectedProduct = shop?.menu.find(
    (product) => String(product.id) === productId,
  )
  const hasActiveSubscription = subscription?.status === 'ACTIVE'
  const remainingCredits = subscription?.remaining_credits
  const hasCredits =
    hasActiveSubscription &&
    (remainingCredits === -1 || remainingCredits > 0)
  const canOrder = Boolean(hasActiveSubscription && hasCredits)
  const loadingCurrentRequest =
    Boolean(shopId) && (loading || loadedRequestKey !== requestKey)

  async function placeOrder() {
    if (!shop || !productId || !canOrder) return
    dismissToast()
    setBusy(true)
    try {
      const { data } = await api.post('/orders', {
        shop_id: shop.id,
        product_id: Number(productId),
        size,
        sugar_level: Number(sugarLevel),
        milk_preference: milkPreference,
        extra_shots: Number(extraShots),
      })
      navigate(`/orders/${data.id}/qr`)
    } catch (requestError) {
      notifyError(
        getErrorMessage(requestError, 'Sipariş oluşturulamadı.'),
        placeOrder,
      )
    } finally {
      setBusy(false)
    }
  }

  function submitOrder(event) {
    event.preventDefault()
    placeOrder()
  }

  if (!shopId) {
    return (
      <EmptyState
        action={
          <Link className="button-link" to="/">
            Dükkânları keşfet
          </Link>
        }
        description="Sipariş vermek için önce menüsünden bir ürün seç."
        title="Henüz dükkân seçilmedi"
      />
    )
  }
  if (loadingCurrentRequest) {
    return <LoadingState message="Dükkân ve abonelik bilgileri yükleniyor…" />
  }
  if (shopNotFound) {
    return (
      <EmptyState
        action={
          <Link className="button-link" to="/">
            Dükkânları keşfet
          </Link>
        }
        description="Bağlantıdaki dükkân artık mevcut olmayabilir. Başka bir dükkân seç."
        title="Dükkân bulunamadı"
      />
    )
  }
  if (!shop || loadedRequestKey !== requestKey) {
    return (
      <ErrorState
        message={loadError || 'Dükkân bilgisi yüklenemedi.'}
        onRetry={retryLoad}
        retrying={loading}
      >
        <Link className="text-link" to="/">
          Dükkân listesine dön
        </Link>
      </ErrorState>
    )
  }

  const creditsAfterOrder =
    remainingCredits === -1
      ? 'sınırsız'
      : Math.max(0, (remainingCredits || 0) - 1)

  return (
    <section className="panel form-panel order-panel">
      <h1>Siparişini özelleştir</h1>
      <p className="muted">{shop.name}</p>
      {selectedProduct ? (
        <div className="order-product-summary">
          <span className="muted">Seçilen ürün</span>
          <strong>{selectedProduct.name}</strong>
          <span>{selectedProduct.price_tl.toFixed(2)} TL</span>
        </div>
      ) : (
        <EmptyState
          action={
            <Link className="button-link" to={`/shops/${shop.id}`}>
              Dükkân menüsüne dön
            </Link>
          }
          description="Sipariş verebileceğin ürün bulunmuyor. Başka bir dükkân seçebilirsin."
          title="Sipariş edilebilir ürün yok"
        />
      )}

      <div className="order-credit-summary" aria-live="polite">
        <span className="muted">Kalan kahve hakkın</span>
        <strong>
          {!hasActiveSubscription
            ? 'Aktif abonelik yok'
            : remainingCredits === -1
              ? 'Sınırsız'
              : remainingCredits}
        </strong>
      </div>

      {canOrder ? (
        <p className="notice">
          Bu sipariş sonrası {creditsAfterOrder} kredi kalacak.
        </p>
      ) : (
        <div className="order-subscription-needed">
          <p className="notice">
            {!hasActiveSubscription
              ? 'Sipariş verebilmek için aktif bir abonelik gerekli.'
              : 'Kahve hakkın bitmiş. Sipariş vermek için paketini yenile veya yükselt.'}
          </p>
          <Link className="button-link" to="/subscriptions">
            Abonelik paketlerini gör
          </Link>
        </div>
      )}

      {selectedProduct && (
        <form className="form-stack" onSubmit={submitOrder}>
          <label>
            Boyut
            <select onChange={(event) => setSize(event.target.value)} value={size}>
              <option value="S">S</option>
              <option value="M">M</option>
              <option value="L">L</option>
            </select>
          </label>
          <label>
            Süt tipi
            <select
              onChange={(event) => setMilkPreference(event.target.value)}
              value={milkPreference}
            >
              <option value="WHOLE">Normal süt</option>
              <option value="OAT">Yulaf sütü</option>
              <option value="ALMOND">Badem sütü</option>
              <option value="LACTOSE_FREE">Laktozsuz süt</option>
              <option value="NONE">Sütsüz</option>
            </select>
          </label>
          <label>
            Şeker miktarı
            <select
              onChange={(event) => setSugarLevel(event.target.value)}
              value={sugarLevel}
            >
              {[0, 1, 2, 3, 4, 5].map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </select>
          </label>
          <label>
            Ek shot
            <select
              onChange={(event) => setExtraShots(event.target.value)}
              value={extraShots}
            >
              {[0, 1, 2, 3].map((count) => (
                <option key={count} value={count}>
                  {count}
                </option>
              ))}
            </select>
          </label>
          <button
            disabled={busy || !productId || !canOrder}
            type="submit"
          >
            {busy ? 'Sipariş veriliyor…' : 'Siparişi Onayla'}
          </button>
        </form>
      )}
    </section>
  )
}
