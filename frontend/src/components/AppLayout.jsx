import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { getErrorMessage } from '../api/client.js'
import { useToast } from '../context/useToast.js'
import { useAuth } from '../context/useAuth.js'

export function AppLayout() {
  const { isAuthenticated, signOut, user } = useAuth()
  const { dismissToast, notifyError } = useToast()
  const navigate = useNavigate()

  async function handleSignOut() {
    dismissToast()
    try {
      await signOut()
    } catch (error) {
      notifyError(
        getErrorMessage(error, 'Sunucu oturumu kapatılamadı; bu cihazdan çıkış yapıldı.'),
      )
    } finally {
      navigate('/')
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink className="brand" to="/">
          KahveCell
        </NavLink>
        <nav className="nav-links" aria-label="Ana menü">
          <NavLink end to="/">Dükkânlar</NavLink>
          {isAuthenticated ? (
            <>
              {user?.role === 'SHOP_OWNER' ? (
                <NavLink to="/owner/orders">Sipariş yönetimi</NavLink>
              ) : (
                <>
                  <NavLink to="/subscriptions">Abonelik</NavLink>
                  <NavLink to="/orders/history">Siparişlerim</NavLink>
                </>
              )}
              <span className="muted">{user?.full_name || user?.phone_number}</span>
              <button className="nav-button" onClick={handleSignOut} type="button">
                Çıkış
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login">Giriş</NavLink>
              <NavLink to="/register">Kayıt</NavLink>
            </>
          )}
        </nav>
      </header>
      <main className="page">
        <Outlet />
      </main>
    </div>
  )
}
