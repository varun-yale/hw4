import { Link } from 'react-router-dom'
import { formatPrice, SIZES, type ChatProductCard, type Product } from '../api'
import { swatch } from '../design'

function shorten(text: string, max = 90) {
  return text.length <= max ? text : text.slice(0, text.lastIndexOf(' ', max)) + '…'
}

type CardProduct = ChatProductCard & Partial<Pick<Product, 'category' | 'sizes_in_stock'>>

// Used by the Products page, Home, and chat search results, so every card opens the same detail page.
export default function ProductCard({ product }: { product: CardProduct }) {
  const sizes = product.sizes_in_stock
  const limited = sizes && sizes.length > 0 && sizes.length < SIZES.length
  return (
    <Link to={`/products/${product.product_id}`} className="card">
      <div className="card-media">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {product.total_stock === 0 ? (
          <span className="card-flag flag-out">Sold out</span>
        ) : (
          limited && <span className="card-flag flag-low">{sizes.length} of 6 sizes left</span>
        )}
        <span className="card-cta">View details →</span>
      </div>
      <div className="card-body">
        <p className="card-eyebrow">{product.category ?? product.garment_type}</p>
        <h3>{product.name}</h3>
        <p className="muted">{shorten(product.description)}</p>
        <div className="card-foot">
          <p className="price">{formatPrice(product.price)}</p>
          <span className="swatches" aria-label={`Colors: ${product.colors.join(', ')}`}>
            {product.colors.slice(0, 4).map((c) => (
              <span key={c} className="swatch" style={{ background: swatch(c) }} title={c} />
            ))}
            {product.colors.length > 4 && <span className="swatch-more">+{product.colors.length - 4}</span>}
          </span>
        </div>
        {product.total_stock === 0 && <p className="sold-out">Sold out</p>}
      </div>
    </Link>
  )
}
