// Hash routing: `#/knapsack` shows the Knapsack page.

// `icon`: the path of a 24x24 line icon, drawn in the sidebar
export const pages = [
  { path: '/', label: 'How it works', icon: 'M4 6h16M4 12h10M4 18h7' },
  {
    path: '/knapsack',
    label: 'Knapsack',
    icon: 'M6 8h12l-1 12H7L6 8zM9 8V6a3 3 0 0 1 6 0v2',
  },
  {
    path: '/function',
    label: 'Find a maximum',
    icon: 'M3 17c3 0 3-10 6-10s3 8 6 8 3-11 6-11',
  },
  { path: '/saved', label: 'Open a saved run', icon: 'M3 7h6l2 2h10v10H3V7z' },
] as const

export type PagePath = (typeof pages)[number]['path']

function current(): PagePath {
  const path = location.hash.replace(/^#/, '') || '/'
  return pages.some((p) => p.path === path) ? (path as PagePath) : '/'
}

export const route = $state({ path: current() })

window.addEventListener('hashchange', () => {
  route.path = current()
})
