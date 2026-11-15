import { describe, expect, it } from 'vitest'
import { createSseParser } from './sse'

describe('createSseParser', () => {
  it('returns complete events and ignores comments and blank lines', () => {
    const parse = createSseParser()
    expect(parse(': keep-alive\n\ndata: {"delta":"Hi"}\n\ndata: {"done":true}\n\n')).toEqual([
      { delta: 'Hi' },
      { done: true },
    ])
  })

  it('joins an event split across two chunks', () => {
    const parse = createSseParser()
    expect(parse('data: {"del')).toEqual([])
    expect(parse('ta":"lo"}\n')).toEqual([{ delta: 'lo' }])
  })

  it('skips a malformed event without throwing', () => {
    const parse = createSseParser()
    expect(parse('data: {oops\ndata: {"delta":"ok"}\n')).toEqual([{ delta: 'ok' }])
  })
})
