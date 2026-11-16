import { describe, expect, it } from 'vitest'
import { highlight } from './highlight'

const TEXT = 'Museums need income to conserve collections. A modest fee funds conservation.'

describe('highlight', () => {
  it('marks a quote and keeps the surrounding text', () => {
    expect(highlight(TEXT, ['a modest fee funds conservation'])).toEqual([
      { text: 'Museums need income to conserve collections. ', quoted: false },
      { text: 'A modest fee funds conservation', quoted: true },
      { text: '.', quoted: false },
    ])
  })

  it('merges overlapping quotes', () => {
    const segs = highlight(TEXT, ['Museums need income', 'need income to conserve'])
    expect(segs[0]).toEqual({ text: 'Museums need income to conserve', quoted: true })
  })

  it('leaves text alone when the quote is absent or too short', () => {
    expect(highlight(TEXT, ['not in the text at all', 'fee'])).toEqual([{ text: TEXT, quoted: false }])
  })

  it('reassembles to the original text', () => {
    const segs = highlight(TEXT, ['income to conserve', 'funds conservation.'])
    expect(segs.map((s) => s.text).join('')).toBe(TEXT)
  })

  it('keeps positions right when a character changes length in lower case', () => {
    const text = 'İstanbul made buses free and ridership rose.'
    expect(highlight(text, ['ridership rose']).find((s) => s.quoted)?.text).toBe('ridership rose')
  })

  it('treats punctuation in a quote as plain text', () => {
    expect(highlight('Is it fair (really fair) to charge?', ['(really fair)']).find((s) => s.quoted)?.text).toBe('(really fair)')
  })
})
