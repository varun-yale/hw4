import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchProducts, SIZES, type Product } from '../api'
import { useChatResults } from '../chatResults'
import ProductCard from '../components/ProductCard'

const PRICE_RANGES: Record<string, { label: string; min: number; max: number }> = {
  any: { label: 'Any price', min: 0, max: Infinity },
  under40: { label: 'Under $40', min: 0, max: 39.99 },
  '40to60': { label: '$40 – $60', min: 40, max: 60 },
  '60to80': { label: '$60 – $80', min: 60.01, max: 80 },
  over80: { label: 'Over $80', min: 80.01, max: Infinity },
}

const SORTS: Record<string, { label: string; compare: (a: Product, b: Product) => number }> = {
  name: { label: 'Name (A–Z)', compare: (a, b) => a.name.localeCompare(b.name) },
  priceLow: { label: 'Price: low to high', compare: (a, b) => a.price - b.price || a.name.localeCompare(b.name) },
  priceHigh: { label: 'Price: high to low', compare: (a, b) => b.price - a.price || a.name.localeCompare(b.name) },
  stock: { label: 'Most in stock', compare: (a, b) => b.total_stock - a.total_stock },
}

export default function Products() {
  const { results, clearResults } = useChatResults()
  const [products, setProducts] = useState<Product[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  // Filters live in the URL (?category=Hoodies&size=M…), so Back and shared links keep them.
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const category = params.get('category') ?? 'all'
  const price = params.get('price') ?? 'any'
  const size = params.get('size') ?? 'any'
  const inStockOnly = params.get('instock') === '1'
  const sort = params.get('sort') ?? 'name'

  // The router applies URL changes a moment later, so keep our own copy of the newest filters.
  // Otherwise a quick "Clear filters" followed by typing could bring the old filters back.
  const latest = useRef(params)
  useEffect(() => {
    latest.current = params
  }, [params])

  function setParam(key: string, value: string, defaultValue: string) {
    const next = new URLSearchParams(latest.current)
    if (value === defaultValue) next.delete(key)
    else next.set(key, value)
    latest.current = next
    setParams(next, { replace: true })
  }

  function clearFilters() {
    latest.current = new URLSearchParams()
    setParams(latest.current, { replace: true })
  }

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    if (results) window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [results])

  const categories = useMemo(() => {
    const counts = new Map<string, number>()
    products?.forEach((p) => counts.set(p.category, (counts.get(p.category) ?? 0) + 1))
    return [...counts.entries()].sort((a, b) => b[1] - a[1])
  }, [products])

  const visible = useMemo(() => {
    if (!products) return []
    const range = PRICE_RANGES[price] ?? PRICE_RANGES.any
    const words = q.toLowerCase().split(/\s+/).filter(Boolean)
    return products
      .filter((p) => category === 'all' || p.category === category)
      .filter((p) => p.price >= range.min && p.price <= range.max)
      .filter((p) => size === 'any' || (p.sizes_in_stock ?? []).includes(size))
      .filter((p) => !inStockOnly || p.total_stock > 0)
      .filter((p) => {
        const text = `${p.name} ${p.description} ${p.colors.join(' ')} ${p.search_tags.join(' ')}`.toLowerCase()
        return words.every((w) => text.includes(w))
      })
      .sort((SORTS[sort] ?? SORTS.name).compare)
  }, [products, q, category, price, size, inStockOnly, sort])

  const filtersActive = params.toString() !== '' && [...params.keys()].some((k) => k !== 'sort')

  // Search results from the chatbot take over the page until the shopper clears them.
  if (results) {
    return (
      <>
        <div className="chat-results-banner">
          <div>
            <p className="eyebrow">From the shop assistant</p>
            <h1>{results.title}</h1>
            <p className="muted">
              {results.products.length} {results.products.length === 1 ? 'item' : 'items'} for "{results.query}"
            </p>
          </div>
          <button className="btn btn-primary" onClick={clearResults}>
            Show all products
          </button>
        </div>
        <div className="grid chat-results-grid" key={results.id} data-testid="chat-results">
          {results.products.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      </>
    )
  }

  if (error) return <p className="error">Couldn't load products: {error}</p>
  if (!products) return <p className="loading">Loading products…</p>

  return (
    <>
      <header className="shop-head">
        <div>
          <p className="eyebrow">The shop</p>
          <h1>Products</h1>
          <p className="muted">Officially licensed Yale apparel, with live stock for every size.</p>
        </div>
      </header>
      <div className="category-pills" role="radiogroup" aria-label="Category">
        {[['all', products.length] as [string, number], ...categories].map(([c, n]) => (
          <button
            key={c}
            role="radio"
            aria-checked={category === c}
            className={`pill${category === c ? ' active' : ''}`}
            onClick={() => setParam('category', c, 'all')}
          >
            {c === 'all' ? 'All' : c}
            <span>{n}</span>
          </button>
        ))}
      </div>
      <div className="filters" data-testid="filters">
        <input
          className="filter-search"
          type="search"
          placeholder="Search name, color, sport, college…"
          value={q}
          onChange={(e) => setParam('q', e.target.value, '')}
          aria-label="Search products"
        />
        <label>
          Price
          <select aria-label="Price" value={price} onChange={(e) => setParam('price', e.target.value, 'any')}>
            {Object.entries(PRICE_RANGES).map(([k, r]) => (
              <option key={k} value={k}>
                {r.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          In stock in size
          <select aria-label="In stock in size" value={size} onChange={(e) => setParam('size', e.target.value, 'any')}>
            <option value="any">Any size</option>
            {SIZES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label>
          Sort by
          <select aria-label="Sort by" value={sort} onChange={(e) => setParam('sort', e.target.value, 'name')}>
            {Object.entries(SORTS).map(([k, s]) => (
              <option key={k} value={k}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-check">
          <input type="checkbox" checked={inStockOnly} onChange={(e) => setParam('instock', e.target.checked ? '1' : '0', '0')} />
          In stock only
        </label>
      </div>
      <div className="filter-summary">
        <span data-testid="result-count">
          Showing {visible.length} of {products.length} products
        </span>
        {filtersActive && (
          <button className="link-button" onClick={clearFilters}>
            Clear filters
          </button>
        )}
        <span className="muted filter-tip">Tip: ask the chat assistant, e.g. "what hoodies do you have?"</span>
      </div>
      {visible.length === 0 ? (
        <div className="empty-state">
          <p>No products match these filters.</p>
          <button className="btn btn-primary" onClick={clearFilters}>
            Clear filters
          </button>
        </div>
      ) : (
        <div className="grid">
          {visible.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      )}
    </>
  )
}
