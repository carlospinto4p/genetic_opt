<script lang="ts" generics="D">
  import type { Snippet } from 'svelte'
  import type { Member } from '../lib/api'
  import { fmt } from '../lib/format'
  import { geneKey } from '../lib/genes'
  import GeneStrip from './GeneStrip.svelte'

  let {
    population,
    decoded,
    decodedLabel,
    off = () => [],
  }: {
    population: Member<D>[]
    // Left out for a saved run, whose files hold no decoded chromosome
    decoded?: Snippet<[Member<D>]>
    decodedLabel?: string
    off?: (m: Member<D>) => number[]
  } = $props()

  const originLabel = { initial: 'random start', child: 'new child', survivor: 'kept' }

  // A saved run can have genes of any kind, shown as text
  let binary = $derived(population.every((m) => m.genes.every((g) => g === 0 || g === 1)))
  // Not known for a saved run
  let hasOrigin = $derived(population.some((m) => m.origin))

  type Row = {
    rank: number
    member: Member<D>
    score: number
    origin: string
    copies: number
    off: number[]
  }
  type Key = 'rank' | 'score' | 'origin' | 'copies'

  let rows: Row[] = $derived.by(() => {
    const keys = population.map((m) => geneKey(m.genes))
    const counts = new Map<string, number>()
    for (const key of keys) counts.set(key, (counts.get(key) ?? 0) + 1)
    return population.map((member, i) => ({
      rank: i + 1,
      member,
      score: member.score,
      origin: member.origin ?? '',
      copies: counts.get(keys[i]) ?? 1,
      off: binary ? off(member) : [],
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
        {#if decoded}<th>{decodedLabel}</th>{/if}
        <th class="sortable num" onclick={() => sortBy('score')}>Score{arrow('score')}</th>
        {#if hasOrigin}
          <th class="sortable" onclick={() => sortBy('origin')}>Where from{arrow('origin')}</th>
        {/if}
        <th class="sortable num" onclick={() => sortBy('copies')}>Copies{arrow('copies')}</th>
      </tr>
    </thead>
    <tbody>
      {#each sorted as row (row.rank)}
        <tr>
          <td class="num">{row.rank}</td>
          <td>
            {#if binary}
              <GeneStrip genes={row.member.genes} off={row.off} size={16} />
            {:else}
              <ul class="genes">
                {#each row.member.genes as gene, i (i)}<li><code>{gene}</code></li>{/each}
              </ul>
            {/if}
          </td>
          {#if decoded}<td>{@render decoded(row.member)}</td>{/if}
          <td class="num">{fmt(row.score)}</td>
          {#if hasOrigin && row.member.origin}
            <td><span class="chip origin-{row.origin}">{originLabel[row.member.origin]}</span></td>
          {/if}
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
  .genes {
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .genes code {
    overflow-wrap: anywhere;
  }
  .origin-child {
    background: var(--accent-dim);
    color: var(--accent);
  }
</style>
