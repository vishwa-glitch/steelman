import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

// The report card must show exactly what the eval runner wrote. If this fails, run `npm run sync-evals`.
const here = dirname(fileURLToPath(import.meta.url))
const backend = join(here, '../../backend/evals/results')
const site = join(here, '../src/data/evals')

describe('eval results shown on the site', () => {
  it.skipIf(!existsSync(backend))('match the backend results files', () => {
    const files = readdirSync(backend).filter((f) => f.endsWith('.json'))
    expect(files.length).toBeGreaterThan(0)
    for (const file of files) {
      const source = JSON.parse(readFileSync(join(backend, file), 'utf8'))
      const shown = JSON.parse(readFileSync(join(site, file), 'utf8'))
      expect(shown, file).toEqual({ meta: source.meta, summary: source.summary })
    }
  })
})
