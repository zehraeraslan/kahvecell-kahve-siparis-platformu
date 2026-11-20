import { Outlet } from 'react-router-dom'

export function AuthLayout() {
  return (
    <main className="auth-screen">
      <Outlet />
    </main>
  )
}
