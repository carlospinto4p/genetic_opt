<script lang="ts" generics="D">
  import type { Snippet } from 'svelte'
  import type { Member } from '../lib/api'
  import { fmt } from '../lib/format'
  import GeneStrip from './GeneStrip.svelte'

  let {
    population,
    decoded,
    decodedLabel,
    off = () => [],
  }: {
    population: Member<D>[]
    decoded: Snippet<[Member<D>]>
    decodedLabel: string
    off?: (m: Member<D>) => number[]
  } = $props()

  const originLabel = { initial: 'random start', child: 'new child', survivor: 'kept' }

  type Row = { rank: number; member: Member<D>; score: number; origin: string; copies: number }
  type Key = 'rank' | 'score' | 'origin' | 'copies'

  let rows: Row[] = $derived.by(() => {
    const counts = new Map<string, number>()
    for (const m of population) {
      const key = m.genes.join('')
      counts.set(key, (counts.get(key) ?? 0) + 1)
    }
    return population.map((member, i) => ({
      rank: i + 1,
      member,
      score: member.score,
      origin: member.origin,
      copies: counts.get(member.genes.join('')) ?? 1,
    }))
  })

  let sortKey = $state<Key>('rank')
  let dir = $state<1 | -1>(1)

  function sortBy(key: Key) {
    if (sortKey === key) dir = dir === 1 ? -1 : 1
    else {
      sortKey = key
      dir = 1
    }
  }

  let sorted = $derived.by(() => {
    const k = sortKey
    return [...rows].sort((a, b) => {
      const av = a[k]
      const bv = b[k]
      return (av < bv ? -1 : av > bv ? 1 : a.rank - b.rank) * dir
    })
  })

  const arrow = (key: Key) => (sortKey === key ? (dir === 1 ? ' ▲' : ' ▼') : '')
</script>

<div class="wrap">
  <table>
    <thead>
      <tr>
        <th class="sortable num" onclick={() => sortBy('rank')}>Rank{arrow('rank')}</th>
        <th>Genes</th>
        <th>{decodedLabel}</th>
        <th class="sortable num" onclick={() => sortBy('score')}>Score{arrow('score')}</th>
        <th class="sortable" onclick={() => sortBy('origin')}>Where from{arrow('origin')}</th>
        <th class="sortable num" onclick={() => sortBy('copies')}>Copies{arrow('copies')}</th>
      </tr>
    </thead>
    <tbody>
      {#each sorted as row (row.rank)}
        <tr>
          <td class="num">{row.rank}</td>
          <td><GeneStrip genes={row.member.genes} off={off(row.member)} size={16} /></td>
          <td>{@render decoded(row.member)}</td>
          <td class="num">{fmt(row.score)}</td>
          <td><span class="chip origin-{row.origin}">{originLabel[row.member.origin]}</span></td>
          <td class="num">{row.copies}</td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .wrap {
    overflow-x: auto;
    max-height: 560px;
    overflow-y: auto;
  }
  thead th {
    position: sticky;
    top: 0;
    background: var(--bg-surface);
    z-index: 1;
  }
  .origin-child {
    background: var(--accent-dim);
    color: var(--accent);
  }
</style>
