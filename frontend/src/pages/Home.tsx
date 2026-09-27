import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, type Product } from '../api'
import ProductCard from '../components/ProductCard'
import { askAssistant, RESIDENTIAL_COLLEGES } from '../design'

// Hand-picked for the hero collage and featured row (all real catalogue items).
const HERO_IDS = ['basic-hoodie-big-yale', '2025-yale-vs-harvard-t-shirt', 'morse-1-4-zip']
const FEATURED_IDS = ['district-vit-hoodie-vintage-bulldog', 'boola-boola-t-shirt', 'yale-mom-crewneck', 'benjamin-franklin-fleece-jacket']

const CATEGORY_ORDER = ['Hoodies', 'Crewnecks', 'T-shirts', 'Quarter-zips', 'Fleece & jackets']
const CATEGORY_COVER: Record<string, string> = {
  Hoodies: 'district-vit-hoodie-vintage-sailor-bulldog',
  Crewnecks: 'baseball-left-chest-crewneck',
  'T-shirts': 'boola-boola-t-shirt',
  'Quarter-zips': 'branford-1-4-zip',
  'Fleece & jackets': 'saybrook-sweater-fleece-jacket',
}

export default function Home() {
  const [products, setProducts] = useState<Product[]>([])

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch(() => setProducts([]))
  }, [])

  const byId = useMemo(() => new Map(products.map((p) => [p.product_id, p])), [products])
  const hero = HERO_IDS.map((id) => byId.get(id)).filter(Boolean) as Product[]
  const featured = FEATURED_IDS.map((id) => byId.get(id)).filter((p): p is Product => !!p && p.total_stock > 0)

  const categories = CATEGORY_ORDER.map((name) => {
    const items = products.filter((p) => p.category === name)
    const cover = byId.get(CATEGORY_COVER[name]) ?? items[0]
    return { name, count: items.length, cover }
  }).filter((c) => c.count > 0)

  const colleges = RESIDENTIAL_COLLEGES.map((college) => ({
    college,
    count: products.filter((p) => p.name.toLowerCase().includes(college.toLowerCase())).length,
  })).filter((c) => c.count > 0)

  return (
    <div className="home">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Officially licensed · New Haven, CT</p>
          <h1>
            Bulldog pride,
            <br />
            <em>worn well.</em>
          </h1>
          <p className="hero-lede">
            Hoodies, crewnecks, and tees for students, alumni, and the families cheering from the stands.
            From your residential college to your varsity team, find the piece that says where you belong.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="btn btn-primary btn-lg">
              Shop the collection
            </Link>
            <button className="btn btn-ghost btn-lg" onClick={() => askAssistant('Can you help me find a gift?')}>
              Ask our shop assistant
            </button>
          </div>
          <ul className="hero-facts">
            <li>
              <strong>{products.length || 102}</strong> styles
            </li>
            <li>
              <strong>{colleges.length || 14}</strong> colleges represented
            </li>
            <li>
              <strong>XS–XXL</strong> live size stock
            </li>
          </ul>
        </div>
        <div className="hero-art" aria-hidden={hero.length === 0}>
          <div className="pennant">
            <span>YALE</span>
          </div>
          {hero.map((p, i) => (
            <Link key={p.product_id} to={`/products/${p.product_id}`} className={`hero-photo hero-photo-${i + 1}`}>
              <img src={p.image_url} alt={p.name} />
              <span className="hero-tag">
                {p.name.replace(/ 1 4 /, ' 1/4 ')} · ${p.price.toFixed(0)}
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Shop by category</p>
            <h2>Find your fit</h2>
          </div>
          <Link to="/products" className="text-link">
            View all products →
          </Link>
        </div>
        <div className="category-grid">
          {categories.map((c) => (
            <Link key={c.name} to={`/products?category=${encodeURIComponent(c.name)}`} className="category-tile">
              {c.cover && <img src={c.cover.image_url} alt="" loading="lazy" />}
              <span className="category-label">
                <strong>{c.name}</strong>
                <span>{c.count} styles</span>
              </span>
            </Link>
          ))}
        </div>
      </section>

      {colleges.length > 0 && (
        <section className="section colleges">
          <div className="colleges-inner">
            <div>
              <p className="eyebrow">Residential colleges</p>
              <h2>Represent your college</h2>
              <p className="muted">
                Every Yale student belongs to one. Find crests and quarter-zips for yours, or for the one you
                still root for years later.
              </p>
            </div>
            <div className="college-chips">
              {colleges.map((c) => (
                <Link key={c.college} to={`/products?q=${encodeURIComponent(c.college)}`} className="college-chip">
                  {c.college}
                  <span>{c.count}</span>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {featured.length > 0 && (
        <section className="section">
          <div className="section-head">
            <div>
              <p className="eyebrow">Featured</p>
              <h2>Worth a closer look</h2>
            </div>
          </div>
          <div className="grid">
            {featured.map((p) => (
              <ProductCard key={p.product_id} product={p} />
            ))}
          </div>
        </section>
      )}

      <section className="section assistant-band">
        <div>
          <p className="eyebrow">Not sure what to get?</p>
          <h2>Ask our shop assistant</h2>
          <p>
            It checks live stock in your size, finds alternatives when something's sold out, and puts results
            right on the page.
          </p>
        </div>
        <div className="assistant-prompts">
          {['What hoodies do you have?', 'Gift for my dad under $60', 'Show me hockey gear'].map((q) => (
            <button key={q} className="prompt-chip" onClick={() => askAssistant(q)}>
              “{q}”
            </button>
          ))}
        </div>
      </section>
    </div>
  )
}
