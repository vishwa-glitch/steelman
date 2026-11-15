// Copy the judge eval summaries from the backend into the site, so the report card shows the real numbers.
// Only the meta and summary are copied, not every judgment. Run: npm run sync-evals
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const from = join(here, '../../backend/evals/results')
const to = join(here, '../src/data/evals')
if (!existsSync(from)) {
  console.log('No backend eval results found; keeping the committed copies.')
  process.exit(0)
}
mkdirSync(to, { recursive: true })
for (const file of readdirSync(from).filter((f) => f.endsWith('.json'))) {
  const { meta, summary } = JSON.parse(readFileSync(join(from, file), 'utf8'))
  writeFileSync(join(to, file), JSON.stringify({ meta, summary }, null, 2) + '\n')
  console.log(`synced ${file}`)
}
