<script lang="ts">
  import { pages, route } from '../lib/router.svelte'

  let { name = '', version = '' }: { name?: string; version?: string } = $props()

  const MIN_WIDTH = 180
  const MAX_WIDTH = 420
  const DEFAULT_WIDTH = 260
  const STORAGE_KEY = 'genetic_opt.sidebarWidth'

  function loadWidth(): number {
    try {
      const raw = Number(localStorage.getItem(STORAGE_KEY))
      return raw >= MIN_WIDTH && raw <= MAX_WIDTH ? raw : DEFAULT_WIDTH
    } catch {
      return DEFAULT_WIDTH
    }
  }

  function saveWidth() {
    try {
      localStorage.setItem(STORAGE_KEY, String(width))
    } catch {
      // The width is only kept for this visit
    }
  }

  let width = $state(loadWidth())
  let dragging = $state(false)

  const clamp = (n: number) => Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, n))

  function startResize(e: MouseEvent) {
    e.preventDefault()
    dragging = true
    const startX = e.clientX
    const startW = width
    document.body.style.userSelect = 'none'
    document.body.style.cursor = 'col-resize'
    const onMove = (ev: MouseEvent) => {
      width = clamp(startW + (ev.clientX - startX))
    }
    const onUp = () => {
      dragging = false
      document.body.style.userSelect = ''
      document.body.style.cursor = ''
      saveWidth()
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  function resetWidth() {
    width = DEFAULT_WIDTH
    saveWidth()
  }

  function onHandleKey(e: KeyboardEvent) {
    const step = e.shiftKey ? 24 : 8
    let next = width
    if (e.key === 'ArrowLeft') next = width - step
    else if (e.key === 'ArrowRight') next = width + step
    else if (e.key === 'Home') next = MIN_WIDTH
    else if (e.key === 'End') next = MAX_WIDTH
    else return
    e.preventDefault()
    width = clamp(next)
    saveWidth()
  }
</script>

<aside class="sidebar" class:dragging style="width: {width}px">
  <div class="brand">
    <svg class="brand-mark" viewBox="0 0 24 24" aria-hidden="true">
      <rect x="2" y="8" width="5" height="8" rx="1.5" fill="var(--s1)" />
      <rect x="9.5" y="8" width="5" height="8" rx="1.5" fill="var(--s2)" />
      <rect x="17" y="8" width="5" height="8" rx="1.5" fill="var(--s1)" />
    </svg>
    <div class="brand-text">
      <div class="brand-name">{name || 'genetic_opt'}</div>
      <div class="brand-sub">{version ? `v${version}` : ''}</div>
    </div>
  </div>

  <nav>
    {#each pages as page (page.path)}
      {@const active = route.path === page.path}
      <a
        href={`#${page.path}`}
        class="nav-item"
        class:active
        aria-current={active ? 'page' : undefined}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            d={page.icon}
            fill="none"
            stroke="currentColor"
            stroke-width={active ? 2.2 : 1.8}
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        <span>{page.label}</span>
        {#if active}<span class="dot"></span>{/if}
      </a>
    {/each}
  </nav>

  <div class="footer muted">Runs use the Python package itself.</div>

  <button
    type="button"
    class="resize-handle"
    aria-label="Resize sidebar"
    onmousedown={startResize}
    ondblclick={resetWidth}
    onkeydown={onHandleKey}
  ></button>
</aside>

<style>
  .sidebar {
    position: relative;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    height: 100%;
    border-right: 1px solid var(--border);
    background: var(--bg-surface);
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 1.1rem 1rem;
    border-bottom: 1px solid var(--border);
  }
  .brand-mark {
    width: 2rem;
    height: 2rem;
    flex-shrink: 0;
  }
  .brand-text {
    min-width: 0;
  }
  .brand-name {
    font-weight: 700;
    font-size: 1.3rem;
    letter-spacing: -0.02em;
  }
  .brand-sub {
    font-family: var(--mono);
    font-size: 1.0625rem;
    color: var(--text-2);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  nav {
    flex: 1;
    overflow-y: auto;
    padding: 0.7rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }
  .nav-item {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.5rem 0.7rem;
    border-radius: 0.55rem;
    border: 1px solid transparent;
    color: var(--text-2);
    text-decoration: none;
  }
  .nav-item svg {
    width: 1.3rem;
    height: 1.3rem;
    flex-shrink: 0;
  }
  .nav-item:hover {
    background: var(--bg-raised);
    color: var(--text);
  }
  .nav-item.active {
    background: var(--accent-dim);
    color: var(--accent);
    border-color: var(--accent-dim);
    font-weight: 600;
  }
  .dot {
    margin-left: auto;
    width: 0.4rem;
    height: 0.4rem;
    border-radius: 50%;
    background: var(--accent);
  }
  .footer {
    border-top: 1px solid var(--border);
    padding: 0.8rem 1rem;
  }
  .resize-handle {
    position: absolute;
    top: 0;
    right: -3px;
    width: 6px;
    height: 100%;
    padding: 0;
    border: none;
    border-radius: 0;
    background: transparent;
    appearance: none;
    cursor: col-resize;
    z-index: 5;
    transition: background 0.12s ease;
  }
  .resize-handle:hover,
  .sidebar.dragging .resize-handle {
    background: var(--accent-dim);
  }
  .resize-handle:focus-visible {
    outline: none;
    background: var(--accent);
  }
  /* On a phone the sidebar sits above the page, its nav in a row */
  @media (max-width: 700px) {
    .sidebar {
      width: 100% !important;
      height: auto;
      border-right: none;
      border-bottom: 1px solid var(--border);
    }
    .brand {
      padding: 0.6rem 1rem;
      border-bottom: none;
    }
    nav {
      flex-direction: row;
      flex-wrap: wrap;
      padding: 0 0.7rem 0.6rem;
    }
    .footer,
    .resize-handle,
    .dot {
      display: none;
    }
  }
</style>
