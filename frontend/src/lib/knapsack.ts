import type { Chromosome } from './api'

/** Genes that ask for an object the decoding leaves out of the bag. */
export function offGenes(c: Chromosome<number[]>): number[] {
  return c.genes.flatMap((g, i) => (g === 1 && c.decoded[i] === 0 ? [i] : []))
}
