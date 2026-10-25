import { afterEach, describe, expect, it, vi } from 'vitest'
import { getInfo } from './api'

// What `fetch` answers, without a server
function answer(status: number, body: string, statusText = '') {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(body, { status, statusText })),
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('request', () => {
  it('fails with the detail the server gives as text', async () => {
    answer(422, JSON.stringify({ detail: 'the population is empty' }))
    await expect(getInfo()).rejects.toThrow(/^the population is empty$/)
  })

  it('fails with the message of each error of a refused request', async () => {
    const detail = [
      { type: 'less_than_equal', loc: ['body', 'n_bits'], msg: 'n_bits is too large' },
      { type: 'missing', loc: ['body', 'low'], msg: 'low is missing' },
    ]
    answer(422, JSON.stringify({ detail }))
    await expect(getInfo()).rejects.toThrow(/^n_bits is too large; low is missing$/)
  })

  it('fails with the status line when the body is not JSON', async () => {
    answer(502, '<html>Bad Gateway</html>', 'Bad Gateway')
    await expect(getInfo()).rejects.toThrow(/^502 Bad Gateway$/)
  })

  it('fails with the status line when the JSON has no detail', async () => {
    answer(500, JSON.stringify({ error: 'boom' }), 'Internal Server Error')
    await expect(getInfo()).rejects.toThrow(/^500 Internal Server Error$/)
  })

  it('gives the JSON of a response that is ok', async () => {
    answer(200, JSON.stringify({ name: 'genetic_opt', version: '1.0.0' }))
    await expect(getInfo()).resolves.toEqual({ name: 'genetic_opt', version: '1.0.0' })
  })
})
