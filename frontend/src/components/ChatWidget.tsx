import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, matchPath, useLocation, useNavigate } from 'react-router-dom'
import {
  clearChatHistory,
  fetchChatHistory,
  formatPrice,
  sendChat,
  type ChatProductCard,
  type ChatTurn,
  type PageContext,
  type ProductResults,
  type StoredChatMessage,
  type User,
} from '../api'
import { useAuth } from '../auth'
import { useChatResults } from '../chatResults'
import { Shield } from './NavBar'

interface Message extends ChatTurn {
  products?: ChatProductCard[]
  results?: ProductResults & { query: string }
  suggestions?: string[] // quick-reply chips (only shown on the latest reply)
  error?: boolean
  skipInHistory?: boolean // failed or blocked turns aren't re-sent to the agent
}

const HISTORY_LIMIT = 12 // earlier turns a guest's browser sends to the agent for context

function greeting(user: User | null, returning = false): Message {
  const content = !user
    ? "Hi! I'm the Campus Customs assistant. Ask me about hoodies, sizes, or gifts."
    : returning
      ? `Welcome back, ${user.first_name}! Here's our conversation from last time.`
      : `Hi ${user.first_name}! I'm the Campus Customs assistant. Ask me about hoodies, sizes, or gifts.`
  return { role: 'assistant', content, skipInHistory: true }
}

// Saved messages from the database -> chat bubbles (search replies get their "view again" link back).
function fromStored(stored: StoredChatMessage[]): Message[] {
  return stored.map((m, i) => {
    const prevUser = stored[i - 1]?.role === 'user' ? stored[i - 1].content : ''
    return {
      role: m.role,
      content: m.content,
      products: m.products,
      results: m.results ? { ...m.results, query: prevUser } : undefined,
    }
  })
}

// Render **bold** segments; everything else stays plain text.
function renderText(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : part,
  )
}

// Tell the agent which products an earlier reply showed, so "the second one" still makes sense later.
function toHistoryTurn(m: Message): ChatTurn {
  const shown = m.results?.products ?? m.products ?? []
  if (!shown.length) return { role: m.role, content: m.content }
  const list = shown.map((p, i) => `${i + 1}. ${p.name} (${p.product_id})`).join('; ')
  return { role: m.role, content: `${m.content}\n[Products shown: ${list}]` }
}

export default function ChatWidget() {
  const { user, loading: authLoading } = useAuth()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([greeting(null)])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const { results: pageResults, showResults } = useChatResults()
  const navigate = useNavigate()
  const location = useLocation()
  const sendRef = useRef<(text: string) => void>(() => {})

  // Logged in: load saved chat from the database. Logged out / guest: start fresh.
  useEffect(() => {
    if (authLoading) return
    if (!user) {
      setMessages([greeting(null)])
      return
    }
    let cancelled = false
    setLoadingHistory(true)
    fetchChatHistory()
      .then((stored) => !cancelled && setMessages([greeting(user, stored.length > 0), ...fromStored(stored)]))
      .catch(() => !cancelled && setMessages([greeting(user)]))
      .finally(() => !cancelled && setLoadingHistory(false))
    return () => {
      cancelled = true
    }
  }, [user, authLoading])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending, open])

  // "Ask about this item" / "Ask our shop assistant" buttons elsewhere on the site open the chat with a question.
  useEffect(() => {
    const onAsk = (e: Event) => {
      setOpen(true)
      sendRef.current((e as CustomEvent<string>).detail)
    }
    window.addEventListener('cc:ask', onAsk)
    return () => window.removeEventListener('cc:ask', onAsk)
  }, [])

  // What the shopper is looking at right now, sent with every message.
  function currentPage(): PageContext {
    const detail = matchPath('/products/:productId', location.pathname)
    return {
      path: location.pathname,
      product_id: detail?.params.productId ?? null,
      results_title: location.pathname === '/products' && pageResults ? pageResults.title : null,
    }
  }

  // Put a set of search results on the Products page.
  function showOnPage(results: ProductResults, query: string) {
    showResults(results, query)
    navigate('/products')
  }

  async function handleNewChat() {
    if (user) await clearChatHistory()
    setMessages([greeting(user)])
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    send(input)
  }

  async function send(raw: string) {
    const text = raw.trim()
    if (!text || sending) return
    // Guests: the browser is the only memory, so send recent turns. Logged-in users: the server
    // loads saved history from the database and ignores this.
    const history: ChatTurn[] = messages
      .filter((m) => !m.error && !m.skipInHistory)
      .slice(-HISTORY_LIMIT)
      .map(toHistoryTurn)
    setMessages((m) => [...m, { role: 'user', content: text }])
    setInput('')
    setSending(true)
    try {
      const { reply, products, results, suggestions, blocked } = await sendChat(text, history, currentPage())
      setMessages((m) => [
        ...(blocked ? m.map((msg, i) => (i === m.length - 1 ? { ...msg, skipInHistory: true } : msg)) : m),
        {
          role: 'assistant',
          content: reply,
          products,
          results: results ? { ...results, query: text } : undefined,
          suggestions,
          skipInHistory: blocked,
        },
      ])
      if (results) showOnPage(results, text)
    } catch (err) {
      setMessages((m) => [
        ...m.map((msg, i) => (i === m.length - 1 ? { ...msg, skipInHistory: true } : msg)),
        { role: 'assistant', content: (err as Error).message, error: true },
      ])
    } finally {
      setSending(false)
    }
  }

  sendRef.current = send

  if (!open) {
    return (
      <button className="chat-toggle" onClick={() => setOpen(true)} aria-label="Open chat">
        <span className="chat-toggle-icon" aria-hidden="true">
          <Shield size={26} />
        </span>
        <span className="chat-toggle-text">
          <strong>Ask the shop</strong>
          <span>Sizes, stock, gift ideas</span>
        </span>
      </button>
    )
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <div className="chat-identity">
          <span className="chat-avatar" aria-hidden="true">
            <Shield size={30} />
            <span className="chat-online" />
          </span>
          <div>
          <div className="chat-title">Shop Assistant</div>
          <div className="chat-subtitle" data-testid="chat-status">
            {user ? `Signed in as ${user.first_name} · chat is saved` : "Guest · chat isn't saved"}
          </div>
          </div>
        </div>
        <div className="chat-header-actions">
          <button className="chat-new" onClick={handleNewChat} title={user ? 'Delete saved chat and start over' : 'Start over'}>
            New chat
          </button>
          <button onClick={() => setOpen(false)} aria-label="Close chat">
            ×
          </button>
        </div>
      </div>
      <div className="chat-messages">
        {loadingHistory && <div className="chat-msg chat-assistant chat-typing">Loading your chat…</div>}
        {messages.map((m, i) => (
          <div key={i} className={`chat-row chat-row-${m.role}`}>
            <div className={`chat-msg chat-${m.role}${m.error ? ' chat-error' : ''}`}>{renderText(m.content)}</div>
            {m.results && (
              <button className="chat-results-link" onClick={() => showOnPage(m.results!, m.results!.query)}>
                🛍️ {m.results.products.length} {m.results.title} shown on the page · view again
              </button>
            )}
            {i === messages.length - 1 && !sending && m.suggestions && m.suggestions.length > 0 && (
              <div className="chat-suggestions" data-testid="chat-suggestions">
                {m.suggestions.map((s) => (
                  <button key={s} className="chat-chip" onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            )}
            {m.products && m.products.length > 0 && (
              <div className="chat-products">
                {m.products.map((p) => (
                  <Link key={p.product_id} to={`/products/${p.product_id}`} className="chat-product">
                    <img src={p.image_url} alt={p.name} />
                    <div>
                      <div className="chat-product-name">{p.name}</div>
                      <div className="chat-product-meta">
                        {formatPrice(p.price)}
                        {p.total_stock === 0 && <span className="sold-out"> · Sold out</span>}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        ))}
        {sending && (
          <div className="chat-msg chat-assistant chat-typing" aria-label="Thinking">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about products, sizes, gifts…"
          maxLength={2000}
        />
        <button type="submit" disabled={sending || loadingHistory}>
          Send
        </button>
      </form>
    </div>
  )
}
