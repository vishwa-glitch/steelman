// With the backend stopped, the site must still work: recorded debates play and live mode says it is resting.
// Run: node e2e/offline.mjs <frontend-url> <screenshot-dir>
import { chromium } from 'playwright-core'

const [base = 'http://localhost:5173', shots = '.'] = process.argv.slice(2)
const browser = await chromium.launch({ channel: 'chrome' })
const check = (ok, what) => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${what}`)
  if (!ok) process.exitCode = 1
}
const page = await (await browser.newContext({ viewport: { width: 1280, height: 900 } })).newPage()
await page.goto(base)
await page.getByRole('status').waitFor({ timeout: 10000 })
check((await page.getByRole('status').innerText()).includes('Live mode is unavailable'), 'home: says live mode is unavailable')
await page.getByLabel('Debate topic').fill('Zoos should be closed.')
check(await page.getByRole('button', { name: 'Start the debate' }).isDisabled(), 'home: start button is disabled even with a topic')
await page.screenshot({ path: `${shots}/home-offline.png`, fullPage: true })
await page.getByRole('link', { name: /Museums should be free/ }).click()
await page.getByText("The judge's verdict").waitFor()
check((await page.locator('.cell p').count()) >= 6 && (await page.locator('.empty').count()) === 0, 'recorded debate: all six turns shown')
check((await page.locator('mark').count()) >= 4, 'recorded debate: quotes highlighted')
await page.screenshot({ path: `${shots}/recorded.png`, fullPage: true })
await page.goto(`${base}/d/some-slug-that-needs-the-server`)
check(await page.getByText('could not be loaded right now').waitFor({ timeout: 10000 }).then(() => true, () => false), 'share link: clear message when the server is down')
await browser.close()
