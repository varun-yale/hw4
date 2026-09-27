import { useEffect } from 'react'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import NavBar, { Shield } from './components/NavBar'
import ChatWidget from './components/ChatWidget'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import About from './pages/About'
import Login from './pages/Login'
import Signup from './pages/Signup'

function NotFound() {
  return (
    <section className="not-found">
      <p className="eyebrow">404</p>
      <h1>This page went to Harvard.</h1>
      <p className="muted">We couldn't find what you were looking for.</p>
      <Link to="/products" className="btn btn-primary">
        Browse the shop
      </Link>
    </section>
  )
}

export default function App() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return (
    <>
      <NavBar />
      <main className="page">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <footer className="footer">
        <div className="footer-inner">
          <div className="footer-brand">
            <Shield size={40} />
            <div>
              <p className="footer-name">Campus Customs</p>
              <p>Officially licensed Yale apparel for students, alumni, and families.</p>
            </div>
          </div>
          <div>
            <p className="footer-heading">Shop</p>
            <Link to="/products?category=Hoodies">Hoodies</Link>
            <Link to="/products?category=Crewnecks">Crewnecks</Link>
            <Link to="/products?category=T-shirts">T-shirts</Link>
            <Link to="/products?category=Quarter-zips">Quarter-zips</Link>
          </div>
          <div>
            <p className="footer-heading">Campus Customs</p>
            <Link to="/about">About us</Link>
            <Link to="/login">Log in</Link>
            <Link to="/signup">Create account</Link>
          </div>
          <div>
            <p className="footer-heading">Visit</p>
            <p>57 Broadway</p>
            <p>New Haven, CT 06511</p>
          </div>
        </div>
        <div className="footer-base">© {new Date().getFullYear()} Campus Customs · Lux et veritas, and a good hoodie.</div>
      </footer>
      <ChatWidget />
    </>
  )
}
