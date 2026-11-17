// Browser check of the whole flow against a local backend running with FAKE_LLM=1 (no AI calls).
// Run: node e2e/debate.mjs <frontend-url> <screenshot-dir>
import { chromium } from 'playwright-core'

const [base = 'http://localhost:5173', shots = '.'] = process.argv.slice(2)
const TURN = 'Free public transport gets cars off the road. When Tallinn made buses free in 2013, ridership rose and the city centre got quieter.'
const browser = await chromium.launch({ channel: 'chrome' })
const check = (ok, what) => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${what}`)
  if (!ok) process.exitCode = 1
}

for (const [name, viewport] of [['desktop', { width: 1280, height: 900 }], ['phone', { width: 390, height: 844 }]]) {
  const page = await (await browser.newContext({ viewport })).newPage()
  const errors = []
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
  page.on('pageerror', (e) => errors.push(String(e)))

  await page.goto(base)
  // topic tools: empty box, Surprise me fills it, categories change the suggestions
  check((await page.getByLabel('Debate topic').inputValue()) === '', `${name}: topic box starts empty`)
  check(await page.getByRole('button', { name: 'Write or pick a topic to start' }).isDisabled(), `${name}: start disabled until a topic is set`)
  await page.getByRole('button', { name: 'Surprise me' }).click()
  check((await page.getByLabel('Debate topic').inputValue()).length > 10, `${name}: Surprise me fills the topic`)
  await page.getByRole('tab', { name: 'Sport' }).click()
  check(await page.getByRole('button', { name: 'Esports should be in the Olympics.' }).isVisible(), `${name}: category shows its topics`)
  await page.getByRole('button', { name: /Start the debate|Write or pick a topic/ }).waitFor()
  await page.screenshot({ path: `${shots}/home-${name}.png`, fullPage: true })
  await page.getByLabel('Debate topic').fill('Public transport should be free.')
  await page.getByRole('button', { name: 'Start the debate' }).click()
  await page.waitForURL(/\/debate\//)

  for (const round of ['opening', 'rebuttal', 'closing']) {
    await page.getByLabel(`Your ${round}`).fill(TURN)
    if (round === 'rebuttal') await page.screenshot({ path: `${shots}/debate-${name}.png`, fullPage: true })
    await page.getByRole('button', { name: 'Submit turn' }).click()
  }
  await page.getByText("The judge's verdict").waitFor({ timeout: 20000 })
  check((await page.locator('.cell p').count()) >= 6 && (await page.locator('.empty').count()) === 0, `${name}: all six turns shown`)
  check((await page.locator('mark').count()) >= 2, `${name}: judge's quotes are highlighted in the transcript`)
  check(await page.getByText('For wins, 28 to 24. You won.').isVisible(), `${name}: verdict headline`)
  await page.screenshot({ path: `${shots}/scorecard-${name}.png`, fullPage: true })

  await page.goto(base)
  check(await page.getByRole('heading', { name: 'Your debates' }).isVisible(), `${name}: finished debate listed under Your debates`)
  check((await page.locator('.mine .card-meta').first().innerText()).includes('you won'), `${name}: Your debates shows the result`)
  await page.goBack()
  await page.getByText("The judge's verdict").waitFor({ timeout: 10000 })
  const shareUrl = await page.locator('.share code').innerText()
  const shared = await (await browser.newContext({ viewport })).newPage()
  await shared.goto(shareUrl)
  await shared.getByText('Shared debate').waitFor()
  check((await shared.getByLabel(/Your /).count()) === 0, `${name}: share page is read-only`)

  // reloading mid-debate restores state from the server
  await page.reload()
  const kept = await page.getByText("The judge's verdict").waitFor({ timeout: 10000 }).then(() => true, () => false)
  check(kept && (await page.locator('.empty').count()) === 0, `${name}: reload keeps the finished debate`)

  await page.getByRole('link', { name: 'How it works', exact: true }).click()
  check(await page.getByText('How the judge is kept honest').waitFor({ timeout: 10000 }).then(() => true, () => false), `${name}: How it works page renders`)
  check((await page.locator('nav .nav-btn.on').innerText()) === 'How it works', `${name}: How it works is the active nav button`)
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)
  check(!overflow, `${name}: no horizontal scroll`)
  check(errors.length === 0, `${name}: no console errors ${errors.slice(0, 2).join(' | ')}`)
}
await browser.close()
