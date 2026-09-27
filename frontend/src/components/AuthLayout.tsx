import type { ReactNode } from 'react'
import { Shield } from './NavBar'

/** Split layout for Log in / Create account: a brand panel beside the form. */
export default function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="auth-layout">
      <aside className="auth-panel" aria-hidden="true">
        <Shield size={64} />
        <p className="auth-panel-title">Welcome to Campus Customs</p>
        <ul>
          <li>Your chat with our shop assistant is saved</li>
          <li>Pick up where you left off on any device</li>
          <li>Live stock in your size on every item</li>
        </ul>
      </aside>
      <section className="auth">
        <h1>{title}</h1>
        <p className="muted auth-sub">{subtitle}</p>
        {children}
      </section>
    </div>
  )
}
