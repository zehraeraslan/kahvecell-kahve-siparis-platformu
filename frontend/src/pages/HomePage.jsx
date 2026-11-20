import { useEffect, useMemo, useState } from 'react'
import L from 'leaflet'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import { Link } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client.js'
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from '../components/FeedbackStates.jsx'
import { useAuth } from '../context/useAuth.js'
import { distanceInKilometers, KIZILAY } from '../utils/geo.js'
import 'leaflet/dist/leaflet.css'
import './HomePage.css'

const shopIcon = L.divIcon({
  className: 'shop-marker',
  html: '<span></span>',
  iconSize: [30, 30],
  iconAnchor: [15, 15],
})

const userIcon = L.divIcon({
  className: 'user-marker',
  html: '<span></span>',
  iconSize: [30, 30],
  iconAnchor: [15, 15],
})

function MapViewport({ locations }) {
  const map = useMap()

  useEffect(() => {
    if (locations.length === 1) {
      map.setView(locations[0], 13, { animate: false })
    } else if (locations.length > 1) {
      map.fitBounds(locations, {
        padding: [32, 32],
        maxZoom: 14,
        animate: false,
      })
    }
  }, [locations, map])

  return null
}

export function HomePage() {
  const { user } = useAuth()
  const [shops, setShops] = useState([])
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)
  const [location, setLocation] = useState(KIZILAY)
  const [locationStatus, setLocationStatus] = useState('requesting')

  useEffect(() => {
    let active = true
    const setFallbackLocation = () => {
      if (active) {
        setLocation(KIZILAY)
        setLocationStatus('fallback')
      }
    }

    if (!navigator.geolocation) {
      setFallbackLocation()
      return () => {
        active = false
      }
    }

    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        if (active) {
          setLocation([coords.latitude, coords.longitude])
          setLocationStatus('available')
        }
      },
      setFallbackLocation,
      { enableHighAccuracy: false, maximumAge: 60_000, timeout: 8_000 },
    )

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    let active = true

    api
      .get('/shops')
      .then(({ data }) => {
        if (active) {
          setShops(data)
          setError('')
        }
      })
      .catch((requestError) => {
        if (active) {
          setError(getErrorMessage(requestError, 'Dükkânlar yüklenemedi.'))
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [reloadKey])

  function retryShops() {
    setLoading(true)
    setError('')
    setReloadKey((key) => key + 1)
  }

  const shopsWithDistance = useMemo(
    () =>
      shops
        .map((shop) => ({
          ...shop,
          distance_km: distanceInKilometers(location, [
            shop.latitude,
            shop.longitude,
          ]),
        }))
        .sort(
          (shopA, shopB) =>
            shopA.distance_km - shopB.distance_km ||
            shopA.name.localeCompare(shopB.name, 'tr'),
        ),
    [location, shops],
  )

  const visibleShops = useMemo(() => {
    const normalizedSearch = search.trim().toLocaleLowerCase('tr')
    if (!normalizedSearch) return shopsWithDistance

    return shopsWithDistance.filter((shop) =>
      `${shop.name} ${shop.address}`
        .toLocaleLowerCase('tr')
        .includes(normalizedSearch),
    )
  }, [search, shopsWithDistance])

  const mapLocations = useMemo(
    () => [location, ...shops.map((shop) => [shop.latitude, shop.longitude])],
    [location, shops],
  )

  return (
    <>
      <header className="home-page-header">
        <div>
          <h1>
            {user
              ? `Hoş geldin${user.full_name ? `, ${user.full_name}` : ''}`
              : 'Ankara kahvecileri'}
          </h1>
          <p className="muted">Yakınındaki kahvecileri keşfet.</p>
        </div>
        <label className="home-search">
          Dükkân ara
          <input
            onChange={(event) => setSearch(event.target.value)}
            placeholder="İsim veya adres yaz"
            type="search"
            value={search}
          />
        </label>
      </header>

      {locationStatus === 'requesting' && (
        <p className="home-location-note" role="status">
          Konumunuz alınıyor…
        </p>
      )}
      {locationStatus === 'fallback' && (
        <p className="home-location-note" role="status">
          Konum paylaşılmadı; Ankara Kızılay gösteriliyor.
        </p>
      )}
      {error && (
        <ErrorState message={error} onRetry={retryShops} retrying={loading} />
      )}

      <section className="home-layout" aria-label="Yakındaki kahveciler">
        <div className="home-shop-list" aria-label="Dükkân listesi">
          {loading ? (
            <LoadingState message="Dükkânlar yükleniyor…" />
          ) : error ? null : visibleShops.length === 0 ? (
            <EmptyState
              action={
                shops.length === 0 ? (
                  <button onClick={retryShops} type="button">
                    Dükkânları yeniden yükle
                  </button>
                ) : (
                  <button onClick={() => setSearch('')} type="button">
                    Aramayı temizle
                  </button>
                )
              }
              description={
                shops.length === 0
                  ? 'Daha sonra tekrar deneyebilir veya yeniden yükleyebilirsin.'
                  : 'Farklı bir isim ya da adres arayabilir veya aramayı temizleyebilirsin.'
              }
              title={
                shops.length === 0 ? 'Henüz dükkân yok' : 'Eşleşme bulunamadı'
              }
            />
          ) : (
            visibleShops.map((shop) => (
              <article className="home-shop-card" key={shop.id}>
                <h2>{shop.name}</h2>
                <p className="home-shop-address">{shop.address}</p>
                <div className="home-shop-meta">
                  <span>
                    <span aria-hidden="true">★</span>{' '}
                    {shop.rating == null
                      ? 'Henüz puanlanmadı'
                      : shop.rating.toFixed(1)}
                  </span>
                  <span>{shop.distance_km.toFixed(2)} km</span>
                </div>
                <Link
                  className="button-link"
                  state={{ distanceKm: shop.distance_km }}
                  to={`/shops/${shop.id}`}
                >
                  Menüyü Gör
                </Link>
              </article>
            ))
          )}
        </div>

        <div className="home-map-frame" aria-label="Dükkânların haritası">
          <MapContainer center={location} zoom={12} scrollWheelZoom>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <MapViewport locations={mapLocations} />
            <Marker icon={userIcon} position={location}>
              <Popup>Bulunduğunuz konum</Popup>
            </Marker>
            {shopsWithDistance.map((shop) => (
              <Marker
                icon={shopIcon}
                key={shop.id}
                position={[shop.latitude, shop.longitude]}
              >
                <Popup>
                  <strong>{shop.name}</strong>
                  <br />
                  {shop.address}
                  <br />
                  <Link
                    state={{ distanceKm: shop.distance_km }}
                    to={`/shops/${shop.id}`}
                  >
                    Menüyü Gör
                  </Link>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
      </section>
    </>
  )
}
