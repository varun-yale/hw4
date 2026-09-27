# Usability improvements (Problem 9)

Four improvements, all built into the running app: two on the front end, two in the agent/backend. Each was tested in the browser, with numbers checked against `campus_customs.db`.

---

## Front end

### 1. Filter and sort on the Products page

**What I added** (`frontend/src/pages/Products.tsx`)
- A filter bar above the 102 products:
  - **Search box** (name, color, sport, college…)
  - **Category** (Crewnecks 28, Hoodies 27, T-shirts 25, Quarter-zips 11, Fleece & jackets 8, Other tops 3)
  - **Price** (Under $40, $40–$60, $60–$80, Over $80)
  - **In stock in size** (XS–XXL, so you only see items you can actually get in your size)
  - **In stock only**
  - **Sort by** name, price low→high, price high→low, or most in stock
- A live **"Showing X of 102 products"** count, a **Clear filters** button, and a friendly empty state when nothing matches.
- Filters are saved in the URL (e.g. `/products?category=Hoodies&size=XL&sort=priceLow`), so they survive a reload, work with the Back button, and can be shared as a link.
- The backend's product list now includes each product's `category` and `sizes_in_stock`, so the size filter uses real inventory.

**Why it helps**
- **Shoppers:** scrolling through 102 cards to find "a hoodie under $70 that comes in XL" is slow. With filters it takes three clicks: Hoodies → XL → 21 results. The size filter also stops people falling for an item only to find their size is gone.
- **The business:** shoppers who find something quickly are more likely to buy, and "sort by most in stock" helps move plentiful inventory.

*Tested:* Hoodies → 27 (SQLite 27). + Over $80 → 2, the same two as SQLite. + in stock in XL → 21 (SQLite 21). Price sort order verified. Filters survive a reload. Search "hockey" → the 5 hockey items (SQLite 5).

### 2. Clearer sizes and sold-out feedback on product pages

**What I added** (`frontend/src/pages/ProductDetail.tsx`)
- An **availability badge** at the top ("In stock in 3 of 6 sizes", plus a "Low stock: …" badge when any size has 5 or fewer).
- A **size picker**: a button for each size labeled *In stock*, *Only N left*, or *Sold out*. Sold-out sizes are greyed out, struck through, and striped, so they're obvious at a glance.
- **Feedback when you pick a size:**
  - In stock: "✓ Size XXL is in stock (25 available)."
  - Low stock: "⚠ Only 2 left in size XXL. Grab it soon."
  - Sold out: "✕ Size M is sold out. Still available in: XS, S, XXL". Each available size is a link that selects it.
- **"Similar items in stock in size M"**: when you pick a sold-out size, the page shows up to 4 similar products that *are* in stock in that size, each with "N left in M". Clicking one opens its product page. This uses the same backend logic as the chatbot's `find_alternatives` tool (improvement 3), through `GET /api/products/{id}/alternatives?size=M`.

**Why it helps**
- **Shoppers:** before, sizes were a flat list, and a sold-out size was a dead end. Now it's clear what you can buy, and a sold-out size immediately points you to your other options.
- **The business:** a sold-out size is where a sale usually gets lost. Showing in-stock substitutes in the shopper's size keeps the sale. The low-stock message also adds healthy urgency.

*Tested:* Ice Hockey Left Chest Hoodie (SQLite XS 20, S 8, M/L/XL 0, XXL 25): badge "In stock in 3 of 6 sizes". Clicking M showed "sold out, still available in XS, S, XXL" and 4 alternatives: 5, 5, 15, 25 left in M, all matching SQLite. Clicking the XXL link showed "in stock (25 available)". Yale Mom Hoodie XXL showed "Only 2 left" (SQLite 2).

---

## Agent / backend

### 3. Real alternatives when something is sold out or unavailable

**What I added**
- A new agent tool, **`find_alternatives(product_id, size, color, max_price)`** in `backend/tools.py`, returning an `AlternativeResults` model (`models.py`):
  - **Only real, available products:** it keeps only products that are **actually in stock in the requested size** (and come in the requested color or fit the budget, if given).
  - **Ranking:** it ranks them by similarity. Same category counts most. Rare shared themes like a sport or college (e.g. "hockey") count more than common words like "Yale". Shared colors and a close price count too.
  - **What it returns:** each alternative with `size_quantity` (how many are left in that size) and a short `why`, plus the original item's `other_sizes_in_stock`.
- **New prompt section** ("Sold out or unavailable: always offer a real alternative"): say it plainly, call `find_alternatives`, offer the best 2–3 with price and stock in the shopper's size, mention other sizes of the original, and never suggest anything a tool didn't return.
- The product page's "Similar items" section (improvement 2) calls the same function, so the website and the chatbot always agree.

**Why it helps**
- **Shoppers:** instead of "sorry, sold out", they get "the Yale Sports Hoodie Hockey ($68, 5 left in M) is the closest match". It's specific, true, and in their size.
- **The business:** it rescues sales that would otherwise be lost. Because suggestions come only from inventory, the bot never sends someone to another sold-out item, which would hurt trust.

*Tested in the chat, on the Ice Hockey hoodie page:* "is this available in medium?" → "sold out in medium… available in XS, S, and XXL. Closest alternatives in medium: Yale Sports Hoodie Hockey ($68, 5 left), Squash Left Chest Hoodie ($68, 5 left), and Fencing Left Chest Hoodie ($68, 15 left)", with product cards and "Check size S" / "Show more hoodies" chips. Every price and quantity matches SQLite.

### 4. Clarifying questions for vague requests, with quick-reply chips

**What I added**
- **`suggestions`** in the agent's structured output (`AgentReply` and `ChatResponse` in `models.py`): up to 4 short quick replies. The chat widget shows them as **tappable chips** under the latest reply; tapping one sends it as the shopper's next message.
- **`too_broad`** on `search_products` results: set when the search had no real filter or matched more than 30 products, so the agent knows a result dump would be unhelpful.
- **New prompt section** ("Vague requests: ask one short question"):
  - For requests like "show me stuff" or "I need a sweatshirt", don't dump dozens of products. Ask **one** short question with 3–4 chips.
  - Specific requests ("what hoodies do you have?", "Morse gear") still go straight to results.
  - Chips must lead to something real. For example, no "Show pink gear" chip when nothing comes in pink.

**Why it helps**
- **Shoppers:** "show me stuff" used to mean scrolling through a huge result set. Now it's one quick question, answered with a tap ("Hoodies"), and then exactly the 27 hoodies. Chips also help on mobile, where typing is slow.
- **The business and cost:** shorter, more focused conversations mean fewer wasted agent calls and tokens, and shoppers are steered toward categories that convert.

*Tested:* "show me stuff" → "Happy to help! What are you shopping for?" with chips [Hoodies, T-shirts, Gifts under $60, College gear], and the page did **not** change. Tapping "Hoodies" → 27 hoodies on the page. "I need a sweatshirt" (38 matches) → "Do you want a crewneck or a hoodie?" with chips [Crewnecks, Hoodies, Quarter-zips, Under $60]. "what hoodies do you have?" still showed all 27 right away.
