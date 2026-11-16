// Play one real debate on a deployed site with the real models. Spends about 5 free AI calls.
// Run: node e2e/live.mjs <site-url> <screenshot-dir>
import { chromium } from 'playwright-core'

const [base, shots = '.'] = process.argv.slice(2)
const TURNS = [
  'Free public transport gets cars off the road and helps people who cannot afford fares. When Tallinn made buses free for residents in 2013, ridership rose, and the city kept the system running for over a decade.',
  'My opponent says fares fund the system, but fares cover only part of running costs in most cities; the rest is already public money. Removing fares also removes ticket machines, inspectors and boarding delays.',
  'The other side never showed that fares, rather than funding choices, keep buses running. Free transport widens access, cuts traffic and costs less than its critics claim. That is why the motion should pass.',
]
const browser = await chromium.launch({ channel: 'chrome' })
const page = await (await browser.newContext({ viewport: { width: 1280, height: 900 } })).newPage()
const errors = []
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
const t0 = Date.now()
const at = () => `${((Date.now() - t0) / 1000).toFixed(1)}s`

await page.goto(base)
await page.getByRole('button', { name: 'Start the debate' }).waitFor()
await page.waitForFunction(() => !document.querySelector('button.primary')?.hasAttribute('disabled'), null, { timeout: 30000 })
console.log(`${at()} home loaded, live mode on`)
await page.getByRole('button', { name: 'Public transport should be free.' }).click()
await page.getByRole('button', { name: 'Start the debate' }).click()
await page.waitForURL(/\/debate\//, { timeout: 60000 })
console.log(`${at()} debate created (topic check passed)`)
for (const [i, round] of ['opening', 'rebuttal', 'closing'].entries()) {
  await page.getByLabel(`Your ${round}`).waitFor({ timeout: 120000 })
  if (i > 0) console.log(`${at()} AI ${['opening', 'rebuttal'][i - 1]} finished`)
  await page.getByLabel(`Your ${round}`).fill(TURNS[i])
  await page.getByRole('button', { name: 'Submit turn' }).click()
  if (round === 'rebuttal') await page.screenshot({ path: `${shots}/live-mid-debate.png`, fullPage: true })
}
await page.getByText('The judge is deliberating').waitFor({ timeout: 120000 })
console.log(`${at()} AI closing finished, judge started`)
await page.getByText("The judge's verdict").waitFor({ timeout: 240000 })
console.log(`${at()} verdict shown: ${await page.locator('.scorecard h2').innerText()}`)
console.log(`   highlighted quotes: ${await page.locator('mark').count()}, empty cells: ${await page.locator('.empty').count()}`)
console.log(`   ${await page.locator('.fineprint').innerText()}`)
await page.screenshot({ path: `${shots}/live-verdict.png`, fullPage: true })
const share = await page.locator('.share code').innerText()
console.log(`   share link: ${share}`)
const p2 = await (await browser.newContext()).newPage()
await p2.goto(share)
await p2.getByText('Shared debate').waitFor({ timeout: 30000 })
console.log(`   share link opens in a fresh browser: yes, read-only: ${(await p2.getByLabel(/Your /).count()) === 0}`)
console.log(`console/page errors: ${errors.length} ${errors.slice(0, 3).join(' | ')}`)
await browser.close()
