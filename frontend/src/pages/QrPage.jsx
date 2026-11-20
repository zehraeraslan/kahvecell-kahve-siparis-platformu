import { useEffect, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { Link, useParams } from 'react-router-dom'
import {
  api,
  getAccessToken,
  getErrorMessage,
} from '../api/client.js'
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from '../components/FeedbackStates.jsx'
import { getOrderStatusLabel } from '../utils/orderStatus.js'
import './OrderStatus.css'

const RECONNECT_DELAY_MS = 2000
const STATUS_RANK = {
  PENDING: 0,
  ACCEPTED: 1,
  PREPARING: 2,
  READY: 3,
  DELIVERED: 4,
}

function parseSseFrame(frame) {
  let eventName = 'message'
  const data = []

  for (const line of frame.split(/\r?\n/)) {
    if (!line || line.startsWith(':')) continue
    const separator = line.indexOf(':')
    const field = separator < 0 ? line : line.slice(0, separator)
    const value = separator < 0 ? '' : line.slice(separator + 1).replace(/^ /, '')
    if (field === 'event') eventName = value
    if (field === 'data') data.push(value)
  }

  return data.length ? { eventName, data: data.join('\n') } : null
}

export function QrPage() {
  const { orderId } = useParams()
  const [order, setOrder] = useState(null)
  const [error, setError] = useState('')
  const [connectionStatus, setConnectionStatus] = useState('connecting')
  const [notFoundOrderId, setNotFoundOrderId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [retryKey, setRetryKey] = useState(0)
  const [loadedOrderId, setLoadedOrderId] = useState(null)

  useEffect(() => {
    let active = true
    let reconnectTimer
    let streamController

    function updateStatus(status) {
      if (!Object.hasOwn(STATUS_RANK, status)) return
      setOrder((currentOrder) => {
        if (
          currentOrder &&
          STATUS_RANK[status] >= STATUS_RANK[currentOrder.status]
        ) {
          return { ...currentOrder, status }
        }
        return currentOrder
      })
    }

    function scheduleReconnect() {
      if (!active) return
      setConnectionStatus('reconnecting')
      reconnectTimer = setTimeout(connectEvents, RECONNECT_DELAY_MS)
    }

    async function connectEvents() {
      if (!active) return
      const controller = new AbortController()
      streamController = controller
      try {
        const token = getAccessToken()
        const response = await fetch(
          api.getUri({ url: `/orders/${orderId}/events` }),
          {
            headers: {
              Accept: 'text/event-stream',
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            signal: controller.signal,
          },
        )

        if (response.status === 401) {
          await api.get(`/orders/${orderId}`)
          if (active) connectEvents()
          return
        }

        if (!response.ok || !response.body) {
          throw new Error('Canlı sipariş bağlantısı kurulamadı.')
        }

        setConnectionStatus('connected')
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        try {
          while (active) {
            const { value, done } = await reader.read()
            if (done) break
            buffer += decoder.decode(value, { stream: true })
            let boundary
            while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
              const frame = buffer.slice(0, boundary.index)
              buffer = buffer.slice(boundary.index + boundary[0].length)
              const message = parseSseFrame(frame)
              if (!message || message.eventName !== 'order_status') continue
              try {
                const event = JSON.parse(message.data)
                if (String(event.order_id) === String(orderId)) {
                  updateStatus(event.status)
                  if (event.status === 'DELIVERED') {
                    controller.abort()
                    return
                  }
                }
              } catch {
                continue
              }
            }
          }
        } finally {
          reader.releaseLock()
        }
        if (active && !controller.signal.aborted) scheduleReconnect()
      } catch {
        if (active && !controller.signal.aborted) scheduleReconnect()
      }
    }

    async function loadOrder() {
      try {
        const { data } = await api.get(`/orders/${orderId}`)
        if (active) {
          setOrder(data)
          setError('')
          setNotFoundOrderId(null)
          setConnectionStatus(
            data.status === 'DELIVERED' ? 'connected' : 'connecting',
          )
          setLoading(false)
          setLoadedOrderId(orderId)
          if (data.status !== 'DELIVERED') connectEvents()
        }
      } catch (requestError) {
        if (active) {
          if (requestError.response?.status === 404) {
            setError('')
            setNotFoundOrderId(orderId)
          } else {
            setError(
              getErrorMessage(
                requestError,
                'Sipariş durumu alınamadı; yeniden deneyin.',
              ),
            )
            setNotFoundOrderId(null)
          }
          setLoading(false)
          setLoadedOrderId(orderId)
        }
      }
    }

    loadOrder()

    return () => {
      active = false
      clearTimeout(reconnectTimer)
      streamController?.abort()
    }
  }, [orderId, retryKey])

  function retryOrder() {
    setError('')
    setNotFoundOrderId(null)
    setLoading(true)
    setRetryKey((key) => key + 1)
  }

  const isLoading = loading || loadedOrderId !== orderId
  const currentOrder = loadedOrderId === orderId ? order : null
  const currentError = loadedOrderId === orderId ? error : ''

  if (notFoundOrderId === orderId) {
    return (
      <EmptyState
        action={
          <Link className="button-link" to="/orders/history">
            Sipariş geçmişine dön
          </Link>
        }
        description="Sipariş numarası hatalı olabilir veya sipariş artık mevcut değildir."
        title="Sipariş bulunamadı"
      />
    )
  }
  if (currentError && !currentOrder) {
    return (
      <ErrorState
        message={currentError}
        onRetry={retryOrder}
        retrying={loading}
      />
    )
  }
  if (isLoading && !currentOrder) {
    return <LoadingState message="Sipariş yükleniyor…" />
  }
  if (!currentOrder) return <LoadingState message="Sipariş yükleniyor…" />

  const isDelivered = currentOrder.status === 'DELIVERED'

  return (
    <section className="panel qr-panel">
      {isDelivered ? (
        <div className="order-complete" role="status">
          <span
            className="order-status-badge is-delivered"
            key={currentOrder.status}
          >
            {getOrderStatusLabel(currentOrder.status)}
          </span>
          <h1>Afiyet olsun!</h1>
          <p className="muted">
            {currentOrder.product_name} siparişin teslim edildi.
          </p>
        </div>
      ) : (
        <>
          <div>
            <h1>Teslim alma QR kodun</h1>
            <p className="muted">
              {currentOrder.product_name} · Sipariş #{currentOrder.id}
            </p>
          </div>
          <div className="qr-code">
            <QRCodeSVG value={currentOrder.qr_code_json} size={280} level="H" />
          </div>
          <div className="qr-status-block">
            <span
              className={`order-status-badge qr-status-badge is-${currentOrder.status.toLowerCase()}`}
              key={currentOrder.status}
              role="status"
            >
              {getOrderStatusLabel(currentOrder.status)}
            </span>
            <p className="muted">
              {connectionStatus === 'connected'
                ? 'Durum canlı olarak güncelleniyor.'
                : 'Canlı bağlantı yenileniyor…'}
            </p>
          </div>
        </>
      )}
      {currentError && (
        <ErrorState
          message={currentError}
          onRetry={retryOrder}
          retrying={loading}
        />
      )}
      <Link className="text-link" to="/orders/history">
        Sipariş geçmişine dön
      </Link>
    </section>
  )
}
