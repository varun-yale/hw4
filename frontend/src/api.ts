export interface SizeStock {
  size: string
  quantity: number
}

export interface Product {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_url: string
  price: number
  total_stock: number
  category: string // Hoodies, Crewnecks, T-shirts, Quarter-zips, Fleece & jackets, Other tops
  sizes_in_stock?: string[] // on the product list
  inventory?: SizeStock[] // on a single product
}

export const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
export const LOW_STOCK = 5

/** A similar in-stock product for when a size is sold out (same logic as the agent's find_alternatives tool). */
export interface Alternative extends Product {
  size_quantity: number | null
  why: string
}

export const fetchAlternatives = (id: string, size: string) =>
  getJson<{ requested_size: string | null; alternatives: Alternative[] }>(
    `/api/products/${encodeURIComponent(id)}/alternatives?size=${encodeURIComponent(size)}`,
  )

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const fetchProducts = () => getJson<Product[]>('/api/products')

export const fetchProduct = (id: string) =>
  getJson<Product>(`/api/products/${encodeURIComponent(id)}`)

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

/** Card data the chat API returns: the same fields the Products page cards use. */
export type ChatProductCard = Pick<
  Product,
  'product_id' | 'name' | 'garment_type' | 'description' | 'colors' | 'price' | 'image_url' | 'total_stock'
>

/** Search results the chat wants shown on the page. */
export interface ProductResults {
  title: string
  products: ChatProductCard[]
}

export interface ChatResponse {
  reply: string
  products: ChatProductCard[] // small cards inside the chat (single-product answers)
  results: ProductResults | null // cards to put on the page (search answers)
  suggestions: string[] // quick-reply chips
  blocked: boolean // content filter blocked the message; don't re-send it as history
}

/** Where the shopper is when they send a message, so "this" can mean the open product. */
export interface PageContext {
  path: string
  product_id: string | null
  results_title: string | null
}

export interface StoredChatMessage extends ChatTurn {
  products: ChatProductCard[]
  results: ProductResults | null
  created_at: string
}

export async function sendChat(message: string, history: ChatTurn[], page: PageContext): Promise<ChatResponse> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history, page }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(typeof data.detail === 'string' ? data.detail : `${res.status} ${res.statusText}`)
  }
  return res.json()
}

export interface User {
  id: number
  first_name: string
  last_name: string
  email: string
}

export interface SignupData {
  first_name: string
  last_name: string
  email: string
  password: string
}

async function postAuth<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api/auth/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    // FastAPI returns a string for our errors, or a list for validation errors
    const detail = typeof data.detail === 'string' ? data.detail : 'Please check the form and try again.'
    throw new Error(detail)
  }
  return data
}

export const signup = (data: SignupData) => postAuth<User>('signup', data)

export const login = (email: string, password: string) =>
  postAuth<User>('login', { email, password })

export const logout = () => postAuth<{ ok: boolean }>('logout')

export async function fetchMe(): Promise<User | null> {
  const res = await fetch('/api/auth/me')
  return res.ok ? res.json() : null
}

/** Saved chat for the logged-in shopper ([] for guests). */
export const fetchChatHistory = () => getJson<StoredChatMessage[]>('/api/chat/history')

export async function clearChatHistory(): Promise<void> {
  await fetch('/api/chat/history', { method: 'DELETE' })
}

export const formatPrice = (price: number) => `$${price.toFixed(2)}`
