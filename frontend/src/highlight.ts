export interface Segment {
  text: string
  quoted: boolean
}

/** Split `text` into quoted and unquoted segments. A quote is matched exactly (ignoring case); quotes the
 * judge reworded slightly are simply not highlighted. Overlapping matches are merged. */
export function highlight(text: string, quotes: string[]): Segment[] {
  const ranges: [number, number][] = []
  for (const q of quotes) {
    const needle = q.trim()
    if (needle.length < 8) continue
    // A case-insensitive search on the original text. Lower-casing both strings first is wrong: a few
    // characters change length when lower-cased, which shifts every position after them.
    const at = text.search(new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i'))
    if (at >= 0) ranges.push([at, at + needle.length])
  }
  ranges.sort((a, b) => a[0] - b[0])
  const merged: [number, number][] = []
  for (const r of ranges) {
    const last = merged[merged.length - 1]
    if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1])
    else merged.push([...r])
  }
  const out: Segment[] = []
  let pos = 0
  for (const [start, end] of merged) {
    if (start > pos) out.push({ text: text.slice(pos, start), quoted: false })
    out.push({ text: text.slice(start, end), quoted: true })
    pos = end
  }
  if (pos < text.length) out.push({ text: text.slice(pos), quoted: false })
  return out
}
