// What the page works out of a `Breeding`, which sends only what it
// cannot: the ranks of the parents and the genes of each child.
import type { Breeding, Child, Gene, GeneOrigin, Member } from './api'

export interface Parent<D = unknown> extends Member<D> {
  rank: number
  kind: 'best' | 'random'
}

// Parent `index` of a breeding: the chromosome of the last generation
// at its rank
export function parentAt<D>(breeding: Breeding, previous: Member<D>[], index: number): Parent<D> {
  const rank = breeding.parents[index]
  return { ...previous[rank], rank, kind: rank < breeding.n_besties ? 'best' : 'random' }
}

// A child's genes before the mutation. The genes are bits, so these
// are its changed ones flipped.
export function crossedGenes(child: Child): Gene[] {
  const changed = new Set(child.changed)
  return child.genes.map((g, i) => (changed.has(i) ? 1 - Number(g) : g))
}

// Which parent each gene of a crossed child came from, `both` where
// the parents have the same gene
export function geneOrigins(crossed: Gene[], a: Gene[], b: Gene[]): GeneOrigin[] {
  return crossed.map((g, i) => (a[i] === b[i] ? 'both' : g === a[i] ? 'a' : 'b'))
}
