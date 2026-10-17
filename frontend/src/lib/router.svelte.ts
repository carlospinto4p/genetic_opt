// Hash routing: `#/knapsack` shows the Knapsack page.

export const pages = [
  { path: '/', label: 'How it works' },
  { path: '/knapsack', label: 'Knapsack' },
  { path: '/function', label: 'Find a maximum' },
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
