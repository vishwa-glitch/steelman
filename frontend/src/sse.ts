/** Parse server-sent events from a text stream. Feed it chunks as they arrive; it returns the complete
 * `data:` payloads found so far and keeps any partial line for the next chunk. */
export function createSseParser() {
  let buffer = ''
  return (chunk: string): unknown[] => {
    buffer += chunk
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    const out: unknown[] = []
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        out.push(JSON.parse(line.slice(6)))
      } catch {
        // a malformed event is skipped; the final "done" event carries the full saved state anyway
      }
    }
    return out
  }
}
