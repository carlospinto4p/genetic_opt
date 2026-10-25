// For the component tests, which run in jsdom. jsdom has no
// `ResizeObserver`, which Svelte uses for `bind:clientWidth`, and no
// `scrollTo` on elements. It lays nothing out, so every element would
// be 0 wide: each is 600 wide instead, as `LineChart` starts, and
// placed at 0.
if (typeof window !== 'undefined') {
  Element.prototype.scrollTo ??= () => {}
  window.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
    configurable: true,
    get: () => 600,
  })
}
