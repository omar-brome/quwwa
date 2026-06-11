// One-off: capture the Form Videos section for the README gallery.
import path from "node:path";
import { chromium } from "playwright";

const BASE = process.env.DEMO_URL ?? "http://localhost:5174";
const ROW_ID = process.argv[2];
const OUT = path.resolve(import.meta.dirname, "../../docs/screenshots/09-form-videos.png");

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 2,
});
await page.goto(`${BASE}/exercise/${ROW_ID}`, { waitUntil: "networkidle" });
await page.getByText("Form videos").waitFor({ timeout: 15000 });
await page.locator("img[src*='ytimg']").first().waitFor({ timeout: 15000 });
await page.waitForTimeout(800);
// open the inline player on the first result
await page.locator("button:has(img[src*='ytimg'])").first().click();
await page.waitForTimeout(3500);
await page.getByText("Form videos").scrollIntoViewIfNeeded();
await page.evaluate(() => window.scrollBy(0, -70));
await page.waitForTimeout(600);
await page.screenshot({ path: OUT });
await browser.close();
console.log("saved", OUT);
