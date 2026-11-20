import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthLayout } from './components/AuthLayout.jsx'
import { AppLayout } from './components/AppLayout.jsx'
import { LoadingState } from './components/FeedbackStates.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import { ToastProvider } from './context/ToastContext.jsx'
import { useAuth } from './context/useAuth.js'
import './App.css'

const HomePage = lazy(() =>
  import('./pages/HomePage.jsx').then((module) => ({ default: module.HomePage })),
)
const LoginPage = lazy(() =>
  import('./pages/LoginPage.jsx').then((module) => ({ default: module.LoginPage })),
)
const RegisterPage = lazy(() =>
  import('./pages/RegisterPage.jsx').then((module) => ({
    default: module.RegisterPage,
  })),
)
const ShopDetailPage = lazy(() =>
  import('./pages/ShopDetailPage.jsx').then((module) => ({
    default: module.ShopDetailPage,
  })),
)
const OrderPage = lazy(() =>
  import('./pages/OrderPage.jsx').then((module) => ({ default: module.OrderPage })),
)
const QrPage = lazy(() =>
  import('./pages/QrPage.jsx').then((module) => ({ default: module.QrPage })),
)
const OrderHistoryPage = lazy(() =>
  import('./pages/OrderHistoryPage.jsx').then((module) => ({
    default: module.OrderHistoryPage,
  })),
)
const SubscriptionPage = lazy(() =>
  import('./pages/SubscriptionPage.jsx').then((module) => ({
    default: module.SubscriptionPage,
  })),
)
const ShopOwnerOrdersPage = lazy(() =>
  import('./pages/ShopOwnerOrdersPage.jsx').then((module) => ({
    default: module.ShopOwnerOrdersPage,
  })),
)
const NotFoundPage = lazy(() =>
  import('./pages/NotFoundPage.jsx').then((module) => ({
    default: module.NotFoundPage,
  })),
)

function ProtectedRoute({ children }) {
  const { isAuthenticated, isReady } = useAuth()

  if (!isReady) {
    return <LoadingState message="Oturum kontrol ediliyor…" />
  }
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

function ShopOwnerRoute({ children }) {
  const { isAuthenticated, isReady, user } = useAuth()

  if (!isReady) {
    return <LoadingState message="Oturum kontrol ediliyor…" />
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return user?.role === 'SHOP_OWNER' ? children : <Navigate to="/" replace />
}

function AppRoutes() {
  return (
    <Suspense fallback={<LoadingState message="Sayfa yükleniyor…" />}>
      <Routes>
        <Route element={<AuthLayout />}>
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
        </Route>
        <Route element={<AppLayout />}>
          <Route index element={<HomePage />} />
          <Route path="shops/:shopId" element={<ShopDetailPage />} />
          <Route
            path="orders/new"
            element={
              <ProtectedRoute>
                <OrderPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="orders/:orderId/qr"
            element={
              <ProtectedRoute>
                <QrPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="orders/history"
            element={
              <ProtectedRoute>
                <OrderHistoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="subscriptions"
            element={
              <ProtectedRoute>
                <SubscriptionPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="owner/orders"
            element={
              <ShopOwnerRoute>
                <ShopOwnerOrdersPage />
              </ShopOwnerRoute>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}

function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppRoutes />
      </ToastProvider>
    </AuthProvider>
  )
}

export default App
