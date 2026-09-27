# Design (Problem 10): "New Haven heritage" storefront

**Goal:** make Campus Customs feel like a real Yale shop on Broadway, not a template. Warm, collegiate, premium, and easy to buy from.

## 1. Color: Yale blue as the accent, not the wallpaper
- **What:** the old site was blue everywhere. Now the background is warm ivory "paper" (`#fbf8f2`) with ink-colored text. **Yale blue** (`#00356b`) is kept for the things you should click or notice: buttons, prices, the active filter, the chat. **Brass** hairlines and small labels add a heritage feel, and a small set of status colors signal stock: green = in stock, amber = low, red = sold out.
- **Why:** when blue only means "clickable" or "important", the next step is obvious. Warm neutrals make the product photos (mostly navy and gray) stand out instead of blending into a blue page. Consistent stock colors mean shoppers read availability at a glance.

## 2. Typography and spacing
- **What:** headings use **Fraunces**, a classic serif with italic accents ("Bulldog pride, *worn well.*"). Everything else uses **Inter** for clean, readable UI text. Small uppercase labels ("SHOP BY CATEGORY") structure each page. There's more whitespace, a 1200px content width, and balanced line breaks on headings.
- **Why:** the serif reads collegiate and premium, like a crest or a diploma, which fits officially licensed Yale gear and supports the price point. The clear heading → label → body order lets people skim to what they want.

## 3. Page layouts and hierarchy
- **Home:**
  - A split hero with the headline, two calls to action, and quick facts (102 styles, 11 colleges represented, live stock XS–XXL), beside a **polaroid collage of real products under a Yale pennant**. Hovering a photo lifts it and shows its name and price.
  - **Shop by category** tiles (image + count), each opening the Products page with that filter already on.
  - **"Represent your college"**: a blue band of chips for every residential college that has merchandise (with item counts), each linking to a filtered search.
  - Featured products, and a band of one-tap example questions for the assistant.
- **Products:** a clear shop header, **category pills** with counts instead of a dropdown, and a clean filter bar (search with an icon, price, size, sort, in stock only).
- **Product page:** a breadcrumb (Products / Hoodies / item). The image stays in view (sticky) with an "Officially licensed" stamp. Then a large serif title and price, **named color swatches**, the size grid, and an **"Ask about this item"** button, with a short list of reassurances below.
- **About:** an editorial layout: big headline, three value cards, a blue quote card with the crest, and a "Visit us at 57 Broadway" card.
- **Log in / Create account:** a split card, with a blue brand panel ("your chat is saved, pick up on any device") beside the form.
- **Footer:** a four-column footer (brand, shop categories, account links, address).
- **Why:** each page now has one obvious main action. Categories and colleges give shoppers a way in that matches how Yale people actually think ("I'm in Saybrook", "I want a hoodie"). That's faster than scrolling 102 products, and it's something a generic store can't offer.

## 4. Product cards and product presentation
- **What:** cards have a warm image backdrop, a category label, a serif price, and **color-swatch dots**. A **"5 of 6 sizes left"** or "Sold out" flag shows when stock is limited. On hover the card lifts, the image zooms slightly, and a "View details →" bar slides up. On the product page, size buttons are clearly In stock / Only N left / Sold out, with sold-out sizes striped and struck through.
- **Why:** shoppers see price, colors, and stock before they click, which means fewer wasted clicks on items that don't come in their size. The hover effects make the grid feel responsive and invite browsing.

## 5. Buttons, filters, forms, navigation
- **What:** pill-shaped buttons in three styles (primary blue, outline, ghost) with a gentle lift on hover. Custom select arrows, soft focus rings, and bigger form fields. A sticky header with a crest logo, an animated underline on the active nav link, a thin announcement bar ("Officially licensed · 57 Broadway · Live size availability"), and a shadow that appears once you scroll. The logo is a CSS/SVG **"CC" shield** (also the new favicon).
- **Why:** consistent controls make the site feel trustworthy. The announcement bar puts the three biggest reasons to buy here up front, and a sticky nav means shopping is always one click away.

## 6. Chat widget integrated into the store
- **What:**
  - **Launcher:** a crest button with a soft pulse ("Ask the shop · Sizes, stock, gift ideas").
  - **Panel:** an ivory panel with a blue header, the shield avatar and a green "online" dot, a clear "Guest · chat isn't saved" / "Signed in · chat is saved" status, and a **New chat** button.
  - **Messages:** rounded bubbles, bouncing typing dots, and quick-reply chips.
  - **Entry points around the site:** the home page's example questions, the hero's "Ask our shop assistant", and each product page's **"Ask about this item"** button all open the chat with the question already sent. On the product page it includes the size you picked.
- **Why:** the assistant now looks like part of the store instead of a bolt-on widget. Putting it next to the product ("Is this available in XXL?") helps at the exact moment a shopper might otherwise leave, and it turns into a real in-stock alternative (see `usability.md`).

## 7. Motion
- **What:** subtle, fast animations (0.2–0.5s): pages fade up in, chat results cards appear one after another, the chat panel scales in, the shield tilts on hover, cards lift, and size feedback slides in. Everything respects **prefers-reduced-motion**.
- **Why:** motion confirms that something happened (results arrived, a size was chosen) without slowing anyone down, and it adds polish.

## 8. Responsive behavior
- **What:**
  - **Header:** below 820px the nav becomes a hamburger menu, and the announcement bar shrinks to one line.
  - **Layouts:** the hero collage stacks under the copy, category pills become a sideways-scrolling row, product grids go to 2 columns, and the size grid goes to 3×2.
  - **Chat:** on phones the chat opens **full-screen**, and the launcher shrinks to a round crest button so it doesn't cover content.
- **Why:** a lot of Yale shopping happens on phones (at the game, walking across campus). Everything stays tappable and readable at 390px wide.

## Visual QA done
I checked Home, Products, a product page (including a sold-out size with alternatives), About, Log in, Create account, and the chat at 1440px (desktop) and 390px (phone). Problems I found and fixed:
- **Blank pages:** a crash caused every page to render blank. A scroll effect returned a Promise in this version of Chrome.
- **Hero collage:** the photos covered each other's captions, and the pennant was hidden.
- **About headline:** "for" was left alone on its own line.
- **Chat header:** the title and "New chat" button wrapped.
- **Phones:** the announcement bar wrapped to two lines, the category pills stacked four rows deep, and the chat launcher covered content.
- **Filters:** a quick "Clear filters" followed by typing could bring back the old filters.
- **Favicon:** there wasn't one, so browsers got a 404. It's now the shield.

All Problem 3–9 features were re-tested in the browser afterwards and still work.
