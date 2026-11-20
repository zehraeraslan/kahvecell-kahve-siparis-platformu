import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client.js'
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from '../components/FeedbackStates.jsx'
import { getOrderStatusLabel } from '../utils/orderStatus.js'
import './OrderStatus.css'

function formatOrderDate(value) {
  return new Intl.DateTimeFormat('tr-TR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function OrderHistoryPage() {
  const [orders, setOrders] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let active = true
    api
      .get('/orders/history')
      .then(({ data }) => {
        if (active) setOrders(data)
      })
      .catch((requestError) => {
        if (active) {
          setError(getErrorMessage(requestError, 'Sipariş geçmişi yüklenemedi.'))
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [reloadKey])

  function retryOrders() {
    setLoading(true)
    setError('')
    setReloadKey((key) => key + 1)
  }

  const sortedOrders = useMemo(
    () =>
      [...orders].sort(
        (orderA, orderB) =>
          new Date(orderB.created_at) - new Date(orderA.created_at) ||
          orderB.id - orderA.id,
      ),
    [orders],
  )

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Sipariş geçmişim</h1>
          <p className="muted">Önceki siparişlerini ve durumlarını gör.</p>
        </div>
      </div>
      {loading ? (
        <LoadingState message="Siparişler yükleniyor…" />
      ) : error ? (
        <ErrorState message={error} onRetry={retryOrders} retrying={loading} />
      ) : sortedOrders.length === 0 ? (
        <EmptyState
          action={
            <Link className="button-link" to="/">
              Dükkânları keşfet
            </Link>
          }
          description="Bir dükkândan kahve sipariş ettiğinde burada listelenecek."
          title="Henüz siparişin yok"
        />
      ) : (
        <div className="table-wrap">
          <table className="order-history-table">
            <thead>
              <tr>
                <th scope="col">Tarih</th>
                <th scope="col">Dükkân</th>
                <th scope="col">Ürün</th>
                <th scope="col">Durum</th>
                <th scope="col">Sipariş</th>
              </tr>
            </thead>
            <tbody>
              {sortedOrders.map((order) => (
                <tr key={order.id}>
                  <td>{formatOrderDate(order.created_at)}</td>
                  <td>{order.shop_name}</td>
                  <td>{order.product_name}</td>
                  <td>
                    <span
                      className={`order-status-badge is-${order.status.toLowerCase()}`}
                    >
                      {getOrderStatusLabel(order.status)}
                    </span>
                  </td>
                  <td>
                    <Link
                      className="text-link"
                      to={`/orders/${order.id}/qr`}
                    >
                      #{order.id}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
