import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchAlternatives, fetchProduct, formatPrice, LOW_STOCK, type Alternative, type Product } from '../api'
import ProductCard from '../components/ProductCard'
import { askAssistant, swatch } from '../design'

type SizeState = 'in' | 'low' | 'out'
const stateOf = (q: number): SizeState => (q === 0 ? 'out' : q <= LOW_STOCK ? 'low' : 'in')

export default function ProductDetail() {
  const { productId } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [alternatives, setAlternatives] = useState<Alternative[] | null>(null)

  useEffect(() => {
    if (!productId) return
    setProduct(null)
    setError(null)
    setSelected(null)
    setAlternatives(null)
    fetchProduct(productId)
      .then(setProduct)
      .catch((e) => setError(String(e)))
  }, [productId])

  const inventory = product?.inventory ?? []
  const selectedQty = inventory.find((s) => s.size === selected)?.quantity
  const inStockSizes = inventory.filter((s) => s.quantity > 0).map((s) => s.size)

  // When a sold-out size is picked, load similar items that ARE in stock in that size.
  useEffect(() => {
    setAlternatives(null)
    if (!product || !selected || selectedQty !== 0) return
    let cancelled = false
    fetchAlternatives(product.product_id, selected)
      .then((r) => !cancelled && setAlternatives(r.alternatives))
      .catch(() => !cancelled && setAlternatives([]))
    return () => {
      cancelled = true
    }
  }, [product, selected, selectedQty])

  if (error)
    return (
      <section className="not-found">
        <h1>We couldn't find that item.</h1>
        <p className="muted">{error}</p>
        <Link to="/products" className="btn btn-primary">Back to the shop</Link>
      </section>
    )
  if (!product) return <p className="loading">Loading…</p>

  const lowSizes = inventory.filter((s) => stateOf(s.quantity) === 'low').map((s) => s.size)

  return (
    <>
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/products" className="back">← Back to products</Link>
        <span aria-hidden="true">/</span>
        <Link to={`/products?category=${encodeURIComponent(product.category)}`}>{product.category}</Link>
        <span aria-hidden="true">/</span>
        <span className="crumb-current">{product.name}</span>
      </nav>
      <div className="detail">
        <div className="detail-media">
          <img src={product.image_url} alt={product.name} />
          <span className="detail-stamp">Officially licensed</span>
        </div>
        <div className="detail-info">
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="price big">{formatPrice(product.price)}</p>
          <p className="detail-desc">{product.description}</p>
          <div className="detail-colors">
            <span className="detail-label">Colors</span>
            <span className="swatches swatches-lg">
              {product.colors.map((c) => (
                <span key={c} className="swatch-named">
                  <span className="swatch" style={{ background: swatch(c) }} />
                  {c}
                </span>
              ))}
            </span>
          </div>

          <div className="availability" data-testid="availability">
            {inStockSizes.length === 0 ? (
              <span className="badge badge-out">Sold out in all sizes</span>
            ) : (
              <span className="badge badge-in">
                In stock in {inStockSizes.length} of {inventory.length} sizes
              </span>
            )}
            {lowSizes.length > 0 && <span className="badge badge-low">Low stock: {lowSizes.join(', ')}</span>}
          </div>

          <div className="size-head">
            <h3>Choose a size</h3>
            <span className="muted">Sizes XS–XXL</span>
          </div>
          <div className="size-picker" role="group" aria-label="Sizes">
            {inventory.map((s) => {
              const state = stateOf(s.quantity)
              return (
                <button
                  key={s.size}
                  className={`size-option size-${state}${selected === s.size ? ' selected' : ''}`}
                  onClick={() => setSelected(s.size)}
                  aria-pressed={selected === s.size}
                  data-testid={`size-${s.size}`}
                >
                  <strong>{s.size}</strong>
                  <span>{state === 'out' ? 'Sold out' : state === 'low' ? `Only ${s.quantity} left` : 'In stock'}</span>
                </button>
              )
            })}
          </div>

          <div className="size-feedback" data-testid="size-feedback" aria-live="polite">
            {!selected && <p className="muted">Pick a size to check availability.</p>}
            {selected && selectedQty !== undefined && selectedQty > LOW_STOCK && (
              <p className="feedback-in">✓ Size {selected} is in stock ({selectedQty} available).</p>
            )}
            {selected && selectedQty !== undefined && selectedQty > 0 && selectedQty <= LOW_STOCK && (
              <p className="feedback-low">
                ⚠ Only {selectedQty} left in size {selected}. Grab it soon.
              </p>
            )}
            {selected && selectedQty === 0 && (
              <div className="feedback-out">
                <p>
                  ✕ Size {selected} is <strong>sold out</strong>.{' '}
                  {inStockSizes.length > 0 ? (
                    <>
                      Still available in:{' '}
                      {inStockSizes.map((s, i) => (
                        <span key={s}>
                          {i > 0 && ', '}
                          <button className="link-button" onClick={() => setSelected(s)}>
                            {s}
                          </button>
                        </span>
                      ))}
                    </>
                  ) : (
                    'No sizes are in stock right now.'
                  )}
                </p>
              </div>
            )}
          </div>

          <div className="detail-actions">
            <button
              className="btn btn-primary btn-lg"
              onClick={() =>
                askAssistant(
                  selected
                    ? `Is the ${product.name} available in ${selected}? If not, what's similar?`
                    : `Tell me more about the ${product.name}. What sizes are in stock?`,
                )
              }
            >
              Ask about this item
            </button>
            <p className="muted">Our assistant checks live stock and can suggest alternatives.</p>
          </div>

          <ul className="detail-perks">
            <li>Officially licensed Yale merchandise</li>
            <li>Stock shown live from our inventory</li>
            <li>Visit us at 57 Broadway, New Haven</li>
          </ul>
        </div>
      </div>

      {selected && selectedQty === 0 && (
        <section className="alternatives" data-testid="alternatives">
          <h2>Similar items in stock in size {selected}</h2>
          {alternatives === null && <p className="muted">Finding similar items…</p>}
          {alternatives?.length === 0 && <p className="muted">No similar items are in stock in {selected} right now.</p>}
          {alternatives && alternatives.length > 0 && (
            <div className="grid">
              {alternatives.map((a) => (
                <div key={a.product_id} className="alt-card">
                  <ProductCard product={a} />
                  <p className="alt-stock">
                    {a.size_quantity} left in {selected}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </>
  )
}
