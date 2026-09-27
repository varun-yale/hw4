import { createContext, useContext, useState, type ReactNode } from 'react'
import type { ProductResults } from './api'

/** Search results from the chatbot, shared between the chat widget and the Products page. */
export interface ChatResults extends ProductResults {
  query: string // what the shopper typed
  id: number // changes on every new result set, so the page can re-animate
}

interface ChatResultsState {
  results: ChatResults | null
  showResults: (results: ProductResults, query: string) => void
  clearResults: () => void
}

const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ChatResults | null>(null)
  const value: ChatResultsState = {
    results,
    showResults: (r, query) => setResults({ ...r, query, id: Date.now() }),
    clearResults: () => setResults(null),
  }
  return <ChatResultsContext.Provider value={value}>{children}</ChatResultsContext.Provider>
}

export function useChatResults() {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside ChatResultsProvider')
  return ctx
}
