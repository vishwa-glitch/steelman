import { beforeEach, describe, expect, it } from 'vitest'
import { forgetDebate, loadDebates, saveDebate } from './history'

class MemoryStorage {
  store = new Map<string, string>()
  getItem(k: string) {
    return this.store.get(k) ?? null
  }
  setItem(k: string, v: string) {
    this.store.set(k, v)
  }
}

describe('your debates', () => {
  beforeEach(() => {
    ;(globalThis as unknown as { localStorage: MemoryStorage }).localStorage = new MemoryStorage()
  })

  it('keeps newest first and merges updates into the same entry', () => {
    saveDebate({ id: 'a', topic: 'A', side: 'pro', startedAt: '1' })
    saveDebate({ id: 'b', topic: 'B', side: 'con', startedAt: '2' })
    saveDebate({ id: 'a', topic: 'A', side: 'pro', startedAt: '1', result: 'won', score: '30–20' })
    const list = loadDebates()
    expect(list.map((d) => d.id)).toEqual(['a', 'b'])
    expect(list[0].result).toBe('won')
  })

  it('forgets an entry', () => {
    saveDebate({ id: 'a', topic: 'A', side: 'pro', startedAt: '1' })
    forgetDebate('a')
    expect(loadDebates()).toEqual([])
  })

  it('survives broken or missing storage', () => {
    ;(globalThis as unknown as { localStorage: unknown }).localStorage = {
      getItem: () => {
        throw new Error('blocked')
      },
      setItem: () => {
        throw new Error('blocked')
      },
    }
    expect(loadDebates()).toEqual([])
    expect(() => saveDebate({ id: 'a', topic: 'A', side: 'pro', startedAt: '1' })).not.toThrow()
  })

  it('ignores junk in storage', () => {
    localStorage.setItem('steelman.debates.v1', '{"not":"a list"}')
    expect(loadDebates()).toEqual([])
  })
})
