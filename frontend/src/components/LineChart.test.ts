// @vitest-environment jsdom
import { fireEvent, render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'
import LineChart from './LineChart.svelte'

function chart(values: (number | null)[][], props = {}) {
  const series = values.map((v, i) => ({ name: `s${i}`, color: 'red', values: v }))
  return render(LineChart, { series, ...props })
}

// The chart is 600 wide and placed at 0 (see `test-setup.ts`), so
// `clientX` is the distance from its left edge.
function hoverAt(svg: Element, clientX: number) {
  return fireEvent.mouseMove(svg, { clientX })
}

describe('LineChart', () => {
  it('draws one line per series, with a label at its end', () => {
    const { container } = chart([
      [1, 2, 3],
      [3, 2, 1],
    ])
    expect(container.querySelectorAll('path')).toHaveLength(2)
    const labels = [...container.querySelectorAll('.end-label')]
    expect(labels.map((l) => l.textContent)).toEqual(['s0', 's1'])
  })

  it('shows a legend only for more than one series', () => {
    expect(chart([[1, 2]]).container.querySelector('.legend')).toBeNull()
  })

  it('leaves a gap for a null value, and keeps the axis to the rest', () => {
    const { container } = chart([[10, 20, null, 30]])
    const d = container.querySelector('path')!.getAttribute('d')!
    // Two pieces: the first two values, then the last one alone
    expect(d.match(/M/g)).toHaveLength(2)
    expect(d.match(/L/g)).toHaveLength(1)
    // The lone last value gets a dot, as a line cannot show it
    expect(container.querySelectorAll('circle')).toHaveLength(1)
    const ticks = [...container.querySelectorAll('.tick[text-anchor="end"]')].map((t) =>
      Number(t.textContent!.replace(/,/g, '')),
    )
    expect(Math.min(...ticks)).toBeGreaterThan(0)
  })

  it('labels a line ending in a gap, and none that is all gaps', () => {
    const { container } = chart([
      [1, 2, null],
      [null, null, null],
    ])
    const labels = [...container.querySelectorAll('.end-label')]
    expect(labels.map((l) => l.textContent)).toEqual(['s0'])
  })

  it('shows the values of the generation under the mouse', async () => {
    const { container } = chart([[5, 6, 7]], { format: (v: number) => `<${v}>` })
    // 600 wide, 60 on the left and 90 on the right: generation 1 at 285
    await hoverAt(container.querySelector('svg')!, 285)
    expect(container.querySelector('.tooltip')!.textContent).toMatch(
      /Generation 1\s+s0\s+<6>/,
    )
  })

  it('says "too large" for a null value under the mouse', async () => {
    const { container } = chart([
      [5, null, 7],
      [1, 2, 3],
    ])
    await hoverAt(container.querySelector('svg')!, 285)
    expect(screen.getByText('too large')).toBeTruthy()
    // A dot on the line that has a value, none on the gap
    expect(container.querySelectorAll('circle[r="4.5"]')).toHaveLength(1)
  })

  it('picks the generation clicked, and moves it with the arrow keys', async () => {
    const onselect = vi.fn()
    const { container } = chart([[1, 2, 3]], { onselect, selected: 1 })
    const svg = container.querySelector('svg')!
    await fireEvent.click(svg, { clientX: 510 })
    await fireEvent.keyDown(svg, { key: 'ArrowRight' })
    await fireEvent.keyDown(svg, { key: 'ArrowLeft' })
    expect(onselect.mock.calls).toEqual([[2], [2], [0]])
  })

  it('draws the selected generation as a line', () => {
    const { container } = chart([[1, 2, 3]], { selected: 2 })
    expect(container.querySelector('line.selected')).not.toBeNull()
  })
})
