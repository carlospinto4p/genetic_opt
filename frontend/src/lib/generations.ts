import type { Generation, Member } from './api'

/**
 * The generation at `index`, or the last one when `index` is past it, as
 * it is while a new, shorter run replaces the one `index` was set on.
 * `previous` is the population before it, empty for the first one.
 */
export function generationAt<D>(
  generations: Generation<D>[],
  index: number,
): { generation: Generation<D>; previous: Member<D>[] } {
  const i = Math.min(index, generations.length - 1)
  return {
    generation: generations[i],
    previous: generations[i - 1]?.population ?? [],
  }
}
