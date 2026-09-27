/** Small shared helpers for the storefront design. */

// Catalogue color names -> swatch colors for the little color dots on cards and product pages.
const SWATCHES: Record<string, string> = {
  black: '#1d1d1f', blue: '#2f5fa7', 'royal blue': '#2446a8', 'light blue': '#9cc3e6', navy: '#14284b',
  'navy blue': '#14284b', white: '#ffffff', ivory: '#f6f0dd', cream: '#efe6cf', gray: '#8e949b',
  'light gray': '#c9ccd1', 'heather gray': '#a9adb2', 'dark heather gray': '#5c6168', 'charcoal gray': '#46494f',
  'dark heather charcoal': '#3d4046', 'heather charcoal gray': '#4a4d53', red: '#b3261e', 'dusty coral': '#d98a7a',
  gold: '#c9a227', yellow: '#e8c547', green: '#2f6b45',
  multicolor: 'conic-gradient(#b3261e, #e8c547, #2f6b45, #2f5fa7, #b3261e)',
}
export const swatch = (color: string) => SWATCHES[color.toLowerCase()] ?? '#b8bcc2'

/** The 14 Yale residential colleges, for the "Find your college" section. */
export const RESIDENTIAL_COLLEGES = [
  'Benjamin Franklin', 'Berkeley', 'Branford', 'Davenport', 'Ezra Stiles', 'Grace Hopper', 'Jonathan Edwards',
  'Morse', 'Pauli Murray', 'Pierson', 'Saybrook', 'Silliman', 'Timothy Dwight', 'Trumbull',
]

/** Open the chat widget and send a message, e.g. from an "Ask about this item" button. */
export function askAssistant(message: string) {
  window.dispatchEvent(new CustomEvent('cc:ask', { detail: message }))
}
