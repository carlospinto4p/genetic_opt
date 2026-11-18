import type { Chromosome, KnapsackProblem } from './api'
import { fmt } from './format'

/**
 * Why the page cannot send a problem, or '' when it can. Past
 * `Number.MAX_SAFE_INTEGER` a number has lost digits already, and from
 * 1e21 `JSON.stringify` writes it as `1e+21`, which the server does not
 * read as a whole number.
 */
export function tooLarge(p: KnapsackProblem): string {
  const over = (n: number) => n > Number.MAX_SAFE_INTEGER
  const limit = `over ${fmt(Number.MAX_SAFE_INTEGER)}, the largest number the page can send`
  const weight = p.weights.findIndex(over)
  if (weight >= 0) return `The weight of object ${weight + 1} is ${limit}.`
  const value = p.values.findIndex(over)
  if (value >= 0) return `The value of object ${value + 1} is ${limit}.`
  if (over(p.capacity)) return `The bag capacity is ${limit}.`
  return ''
}

/** Genes that ask for an object the decoding leaves out of the bag. */
export function offGenes(c: Chromosome<number[]>): number[] {
  return c.genes.flatMap((g, i) => (g === 1 && c.decoded[i] === 0 ? [i] : []))
}
