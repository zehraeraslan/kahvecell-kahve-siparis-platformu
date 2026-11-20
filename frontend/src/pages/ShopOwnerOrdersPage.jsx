import { useEffect, useMemo, useState } from 'react'
import { api, getErrorMessage } from '../api/client.js'
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from '../components/FeedbackStates.jsx'
import { QrScannerDialog } from '../components/QrScannerDialog.jsx'
import { useToast } from '../context/useToast.js'
import { getOrderStatusLabel } from '../utils/orderStatus.js'
import './ShopOwnerOrdersPage.css'
import './OrderStatus.css'

const ORDER_TABS = [
  { status: 'PENDING', label: 'Bekleyen' },
  { status: 'ACCEPTED', label: 'Kabul Edilen' },
  { status: 'PREPARING', label: 'Hazırlanıyor' },
  { status: 'READY', label: 'Hazır' },
]

const NEXT_STATUS = {
  PENDING: 'ACCEPTED',
  ACCEPTED: 'PREPARING',
  PREPARING: 'READY',
}

const MILK_LABELS = {
  WHOLE: 'Normal süt',
  OAT: 'Yulaf sütü',
  ALMOND: 'Badem sütü',
  LACTOSE_FREE: 'Laktozsuz süt',
  NONE: 'Sütsüz',
}

function formatOrderDate(value) {
  return new Intl.DateTimeFormat('tr-TR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function ShopOwnerOrdersPage() {
  const [orders, setOrders] = useState([])
  const [activeTab, setActiveTab] = useState('PENDING')
  const [scanningOrder, setScanningOrder] = useState(null)
  const [actionOrderId, setActionOrderId] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [loading, setLoading] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)
  const { dismissToast, notifyError, notifySuccess } = useToast()

  useEffect(() => {
    let active = true
    let timer

    async function refreshOrders() {
      try {
        const { data } = await api.get('/orders/shop')
        if (active) {
          setOrders(data)
          setLoadError('')
        }
      } catch (requestError) {
        if (active) {
          setLoadError(getErrorMessage(requestError, 'Siparişler yüklenemedi.'))
        }
      } finally {
        if (active) {
          setLoading(false)
          timer = setTimeout(refreshOrders, 5000)
        }
      }
    }

    refreshOrders()
    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [reloadKey])

  function retryOrders() {
    setLoading(true)
    setLoadError('')
    setReloadKey((key) => key + 1)
  }

  const visibleOrders = useMemo(
    () =>
      orders
        .filter((order) => order.status === activeTab)
        .sort(
          (orderA, orderB) =>
            new Date(orderB.created_at) - new Date(orderA.created_at) ||
            orderB.id - orderA.id,
        ),
    [activeTab, orders],
  )
  const firstNonemptyTab = ORDER_TABS.find((tab) =>
    orders.some((order) => order.status === tab.status),
  )

  async function updateOrderStatus(order, nextStatus) {
    dismissToast()
    setActionOrderId(order.id)
    try {
      const { data } = await api.patch(`/orders/${order.id}/status`, {
        status: nextStatus,
      })
      setOrders((currentOrders) =>
        currentOrders.map((currentOrder) =>
          currentOrder.id === order.id ? { ...currentOrder, ...data } : currentOrder,
        ),
      )
      notifySuccess(`${getOrderStatusLabel(nextStatus)} olarak güncellendi.`)
    } catch (requestError) {
      notifyError(
        getErrorMessage(requestError, 'Sipariş durumu güncellenemedi.'),
        () => updateOrderStatus(order, nextStatus),
      )
    } finally {
      setActionOrderId(null)
    }
  }

  async function verifyScannedQr(rawValue) {
    if (!scanningOrder) return

    const scannedOrder = scanningOrder
    const orderId = scannedOrder.id
    setScanningOrder(null)
    dismissToast()
    setActionOrderId(orderId)
    try {
      let payload
      try {
        payload = JSON.parse(rawValue)
      } catch {
        throw new SyntaxError('Okunan QR kod geçerli bir sipariş kodu değil.')
      }
      const { data } = await api.post('/orders/verify-qr', payload)
      if (!data.verified) {
        notifyError(data.message || 'QR kod doğrulanamadı.', () =>
          setScanningOrder(scannedOrder),
        )
        return
      }
      setOrders((currentOrders) =>
        currentOrders.map((order) =>
          order.id === orderId ? { ...order, status: 'DELIVERED' } : order,
        ),
      )
      notifySuccess('QR kod doğrulandı; sipariş teslim edildi.')
    } catch (requestError) {
      notifyError(
        requestError instanceof SyntaxError
          ? 'Okunan QR kod geçerli bir sipariş kodu değil.'
          : getErrorMessage(requestError, 'QR kod doğrulanamadı.'),
        () => setScanningOrder(scannedOrder),
      )
    } finally {
      setActionOrderId(null)
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Sipariş yönetimi</h1>
          <p className="muted">Dükkânlarına gelen siparişleri takip et.</p>
        </div>
      </div>

      <div className="owner-tabs" role="tablist" aria-label="Sipariş durumu">
        {ORDER_TABS.map(({ status, label }) => (
          <button
            aria-selected={activeTab === status}
            className={activeTab === status ? 'is-active' : ''}
            key={status}
            onClick={() => setActiveTab(status)}
            role="tab"
            type="button"
          >
            {label}
            <span>
              {orders.filter((order) => order.status === status).length}
            </span>
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingState message="Siparişler yükleniyor…" />
      ) : loadError ? (
        <ErrorState
          message={loadError}
          onRetry={retryOrders}
          retrying={loading}
        />
      ) : visibleOrders.length === 0 ? (
        <EmptyState
          action={
            !firstNonemptyTab ? (
              <button onClick={retryOrders} type="button">
                Siparişleri yenile
              </button>
            ) : (
              <button
                onClick={() => setActiveTab(firstNonemptyTab.status)}
                type="button"
              >
                Sipariş olan sekmeye geç
              </button>
            )
          }
          description={
            orders.length === 0
              ? 'Yeni sipariş geldiğinde otomatik olarak burada görünecek.'
              : firstNonemptyTab
                ? 'Başka bir durumda sipariş olabilir. Liste 5 saniyede bir yenilenir.'
                : 'Şu anda işlem bekleyen sipariş yok. Yeni siparişler otomatik olarak listelenecek.'
          }
          title={
            orders.length === 0
              ? 'Henüz sipariş yok'
              : firstNonemptyTab
                ? 'Bu sekme boş'
                : 'Aktif sipariş bulunmuyor'
          }
        />
      ) : (
        <section className="owner-order-list" aria-label="Siparişler">
          {visibleOrders.map((order) => {
            const customizations = order.customizations
            const nextStatus = NEXT_STATUS[order.status]
            const isBusy = actionOrderId === order.id

            return (
              <article className="owner-order-card" key={order.id}>
                <header className="owner-order-heading">
                  <div>
                    <h2>{order.product_name}</h2>
                    <p className="muted">
                      {order.shop_name} · Sipariş #{order.id}
                    </p>
                  </div>
                  <span
                    className={`order-status-badge is-${order.status.toLowerCase()}`}
                  >
                    {getOrderStatusLabel(order.status)}
                  </span>
                </header>

                <dl className="owner-order-details">
                  <div>
                    <dt>Müşteri</dt>
                    <dd>
                      {order.customer_name || 'İsim belirtilmemiş'}
                      <br />
                      <span className="muted">{order.customer_phone}</span>
                    </dd>
                  </div>
                  <div>
                    <dt>Özelleştirmeler</dt>
                    <dd>
                      {customizations.size} boy ·{' '}
                      {MILK_LABELS[customizations.milk_preference] ||
                        customizations.milk_preference}{' '}
                      · {customizations.sugar_level} şeker ·{' '}
                      {customizations.extra_shots} ek shot
                    </dd>
                  </div>
                  <div>
                    <dt>Sipariş zamanı</dt>
                    <dd>{formatOrderDate(order.created_at)}</dd>
                  </div>
                </dl>

                {order.status === 'READY' ? (
                  <button
                    disabled={isBusy}
                    onClick={() => setScanningOrder(order)}
                    type="button"
                  >
                    {isBusy ? 'Kontrol ediliyor…' : 'QR Okut'}
                  </button>
                ) : (
                  <button
                    disabled={isBusy}
                    onClick={() => updateOrderStatus(order, nextStatus)}
                    type="button"
                  >
                    {isBusy
                      ? 'Güncelleniyor…'
                      : order.status === 'PENDING'
                        ? 'Kabul Et'
                        : order.status === 'ACCEPTED'
                          ? 'Hazırlamaya Başla'
                          : 'Hazır'}
                  </button>
                )}
              </article>
            )
          })}
        </section>
      )}

      {scanningOrder && (
        <QrScannerDialog
          onClose={() => setScanningOrder(null)}
          onScan={verifyScannedQr}
        />
      )}
    </>
  )
}
