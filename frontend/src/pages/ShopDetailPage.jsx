import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client.js'
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from '../components/FeedbackStates.jsx'
import { distanceInKilometers, KIZILAY } from '../utils/geo.js'
import './ShopDetailPage.css'

const MENU_CATEGORIES = [
  'Espresso Bazlı',
  'Filtre Kahveler',
  'Soğuk İçecekler',
  'Diğer',
]

function categoryForProduct(product) {
  const searchText = `${product.name} ${product.description || ''}`.toLocaleLowerCase(
    'tr',
  )

  if (
    ['soğuk', 'soguk', 'iced', 'cold', 'frappe', 'frappé', 'smoothie'].some(
      (keyword) => searchText.includes(keyword),
    )
  ) {
    return 'Soğuk İçecekler'
  }
  if (
    ['filtre', 'filter', 'v60', 'chemex', 'drip'].some((keyword) =>
      searchText.includes(keyword),
    )
  ) {
    return 'Filtre Kahveler'
  }
  if (
    [
      'espresso',
      'americano',
      'cappuccino',
      'latte',
      'mocha',
      'macchiato',
      'flat white',
      'cortado',
    ].some((keyword) => searchText.includes(keyword))
  ) {
    return 'Espresso Bazlı'
  }
  return 'Diğer'
}

export function ShopDetailPage() {
  const { shopId } = useParams()
  const routeLocation = useLocation()
  const [shop, setShop] = useState(null)
  const [error, setError] = useState('')
  const [notFound, setNotFound] = useState(false)
  const [loading, setLoading] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)
  const [loadedShopId, setLoadedShopId] = useState(null)

  useEffect(() => {
    let active = true
    api
      .get(`/shops/${shopId}`)
      .then(({ data }) => {
        if (active) {
          setShop(data)
          setError('')
          setNotFound(false)
        }
      })
      .catch((requestError) => {
        if (active) {
          if (requestError.response?.status === 404) {
            setError('')
            setNotFound(true)
          } else {
            setNotFound(false)
            setError(
              getErrorMessage(requestError, 'Dükkân bilgisi yüklenemedi.'),
            )
          }
        }
      })
      .finally(() => {
        if (active) {
          setLoadedShopId(shopId)
          setLoading(false)
        }
      })
    return () => {
      active = false
    }
  }, [reloadKey, shopId])

  function retryShop() {
    setLoading(true)
    setError('')
    setNotFound(false)
    setReloadKey((key) => key + 1)
  }

  const groupedMenu = useMemo(() => {
    if (!shop) return []
    return MENU_CATEGORIES.map((category) => ({
      category,
      products: shop.menu.filter(
        (product) => categoryForProduct(product) === category,
      ),
    })).filter((group) => group.products.length > 0)
  }, [shop])

  const isLoading = loading || loadedShopId !== shopId
  if (isLoading) return <LoadingState message="Dükkân yükleniyor…" />
  if (error) {
    return (
      <ErrorState message={error} onRetry={retryShop} retrying={loading}>
        <Link className="text-link" to="/">
          Dükkân listesine dön
        </Link>
      </ErrorState>
    )
  }
  if (notFound || !shop) {
    return (
      <EmptyState
        action={
          <Link className="button-link" to="/">
            Dükkânları keşfet
          </Link>
        }
        description="Başka bir dükkân seçerek menüsünü görebilirsin."
        title="Dükkân bulunamadı"
      />
    )
  }

  const hasRouteDistance = typeof routeLocation.state?.distanceKm === 'number'
  const distanceKm = hasRouteDistance
    ? routeLocation.state.distanceKm
    : distanceInKilometers(KIZILAY, [shop.latitude, shop.longitude])

  return (
    <>
      <header className="shop-detail-header">
        <div>
          <h1>{shop.name}</h1>
          <p className="muted">{shop.address}</p>
        </div>
        <Link
          className="button-link"
          state={{ distanceKm }}
          to={`/orders/new?shopId=${shop.id}`}
        >
          Menüden sipariş ver
        </Link>
      </header>

      <section className="shop-detail-info" aria-label="Dükkân bilgileri">
        <div>
          <span className="muted">Çalışma saatleri</span>
          <strong>{shop.opening_hours || 'Bilgi bulunmuyor'}</strong>
        </div>
        <div>
          <span className="muted">Puan</span>
          <strong>
            {shop.rating == null ? 'Henüz puanlanmadı' : shop.rating.toFixed(1)}
          </strong>
        </div>
        <div>
          <span className="muted">Mesafe</span>
          <strong>
            {distanceKm.toFixed(2)} km
            {!hasRouteDistance && ' · Kızılay’a göre'}
          </strong>
        </div>
      </section>

      <section className="shop-menu" aria-label="Dükkân menüsü">
        <h2>Menü</h2>
        {groupedMenu.length === 0 ? (
          <EmptyState
            action={
              <Link className="button-link" to="/">
                Başka dükkânlara bak
              </Link>
            }
            description="Başka bir dükkân seçebilir veya daha sonra yeniden deneyebilirsin."
            title="Menü henüz hazır değil"
          />
        ) : (
          groupedMenu.map(({ category, products }) => (
            <section className="shop-menu-category" key={category}>
              <h3>{category}</h3>
              <ul className="menu-list">
                {products.map((product) => (
                  <li className="menu-item" key={product.id}>
                    <span>
                      <strong>{product.name}</strong>
                      {product.description && (
                        <>
                          <br />
                          <span className="muted">{product.description}</span>
                        </>
                      )}
                    </span>
                    <span className="shop-menu-actions">
                      <strong>{product.price_tl.toFixed(2)} TL</strong>
                      <Link
                        className="button-link"
                        state={{ distanceKm }}
                        to={`/orders/new?shopId=${shop.id}&productId=${product.id}`}
                      >
                        Sipariş Ver
                      </Link>
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ))
        )}
      </section>
    </>
  )
}
