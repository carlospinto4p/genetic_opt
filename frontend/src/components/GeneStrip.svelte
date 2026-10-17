<script lang="ts">
  import type { Gene, GeneOrigin } from '../lib/api'

  // A Chromosome drawn as one square per gene: filled for 1, empty for
  // 0. Optional marks: the parent each gene came from (a bar under
  // it), the genes the mutation changed (a violet ring), and the genes
  // the decoding turned off (crossed out).
  let {
    genes,
    origins = undefined,
    changed = [],
    off = [],
    size = 22,
    label = '',
  }: {
    genes: Gene[]
    origins?: GeneOrigin[]
    changed?: number[]
    off?: number[]
    size?: number
    label?: string
  } = $props()

  const originName = { a: 'parent A', b: 'parent B', both: 'both parents' }

  function title(i: number): string {
    const parts = [`gene ${i + 1}: ${genes[i]}`]
    if (origins) parts.push(`from ${originName[origins[i]]}`)
    if (changed.includes(i)) parts.push('changed by the mutation')
    if (off.includes(i)) parts.push('turned off when decoded')
    return parts.join(', ')
  }
</script>

<div
  class="strip"
  role="img"
  aria-label={label || `genes ${genes.join('')}`}
  style="--size: {size}px"
>
  {#each genes as gene, i (i)}
    <span
      class="gene"
      class:on={gene === 1}
      class:changed={changed.includes(i)}
      class:off={off.includes(i)}
      title={title(i)}
    >
      {#if origins}
        <span class="origin origin-{origins[i]}"></span>
      {/if}
    </span>
  {/each}
</div>

<style>
  .strip {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 10px 2px;
    padding-bottom: 6px;
    max-width: 100%;
  }
  .gene {
    position: relative;
    width: var(--size);
    height: var(--size);
    border-radius: 4px;
    border: 1.5px solid var(--axis);
    background: var(--gene-off);
    flex-shrink: 0;
  }
  .gene.on {
    background: var(--gene-on);
    border-color: var(--gene-on);
  }
  .gene.changed {
    outline: 3px solid var(--s7);
    outline-offset: 1px;
  }
  .gene.off::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(
      to top right,
      transparent calc(50% - 1.5px),
      var(--critical) calc(50% - 1.5px),
      var(--critical) calc(50% + 1.5px),
      transparent calc(50% + 1.5px)
    );
  }
  .origin {
    position: absolute;
    left: -1px;
    right: -1px;
    bottom: -8px;
    height: 4px;
    border-radius: 2px;
  }
  .origin-a {
    background: var(--s1);
  }
  .origin-b {
    background: var(--s2);
  }
  .origin-both {
    background: var(--axis);
  }
</style>
