/**
 * Drives the running app to capture README assets:
 *   docs/screenshots/*.png, docs/demo-raw.webm, docs/marks.json (GIF cut points)
 *
 * Prereqs: API on :8000 with demo data (backend/scripts/seed_demo.py),
 * frontend dev server, and `npm i --no-save playwright` + chromium.
 *
 *   DEMO_URL=http://127.0.0.1:5174 node scripts/record-demo.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const BASE = process.env.DEMO_URL ?? "http://127.0.0.1:5174";
const DOCS = path.resolve(import.meta.dirname, "../../docs");
const SHOTS = path.join(DOCS, "screenshots");
fs.mkdirSync(SHOTS, { recursive: true });

const t0 = Date.now();
const marks = {};
const mark = (name) => (marks[name] = (Date.now() - t0) / 1000);
const pause = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 2,
  recordVideo: { dir: DOCS, size: { width: 390, height: 844 } },
});
const page = await context.newPage();
const shot = async (name) => {
  await pause(350);
  await page.screenshot({ path: path.join(SHOTS, name) });
  console.log("shot", name);
};

// --- Home: coaching plan, weekly review, volume ---------------------------
await page.goto(BASE, { waitUntil: "networkidle" });
await page.getByText("Push — bench intensity reset").waitFor({ timeout: 15000 });
await pause(800);
await shot("01-home-coaching.png");

await page.getByText("This week", { exact: true }).scrollIntoViewIfNeeded();
await pause(600);
await shot("02-weekly-review.png");

await page.getByText("Weekly sets vs target").scrollIntoViewIfNeeded();
await page.mouse.wheel(0, 220);
await pause(600);
await shot("03-volume-history.png");

await page.mouse.wheel(0, -2000);
await pause(700);

// --- Log a workout (GIF segment starts here) -------------------------------
mark("gifStart");
await page.locator("button.w-full", { hasText: "Start session" }).click();
await page.waitForURL("**/session/active");
await pause(900);

await page.locator("div.fixed.bottom-0 > div > button").first().click();
await pause(600);
await page.getByPlaceholder("Search exercises…").fill("bench");
await pause(900);
await shot("04-picker.png");
await page.locator('.z-50 button:has(div:text-is("Barbell Bench Press"))').click();
await pause(700);

const weight = page.locator("div.fixed.bottom-0 input").nth(0);
const reps = page.locator("div.fixed.bottom-0 input").nth(1);
await weight.fill("90");
await pause(350);
await reps.fill("5");
await pause(350);
await page.locator("div.fixed.bottom-0").getByRole("button", { name: "7", exact: true }).click();
await pause(450);
await page.getByRole("button", { name: "Log set" }).click();
await pause(1100);
await page.getByRole("button", { name: "Log set" }).click();
await pause(1100);
await page.getByRole("button", { name: "Log set" }).click();
await pause(1100);
await shot("05-logging.png");

await page.getByRole("button", { name: "Finish", exact: true }).click();
await pause(700);
await page.locator(".z-50").getByRole("button", { name: "8", exact: true }).click();
await pause(500);
await page.locator(".z-50").getByRole("button", { name: "Finish session" }).click();
await page.waitForURL(/\/session\/(?!active)/, { timeout: 15000 });
await pause(1200);
mark("gifEnd");
await shot("06-session-summary.png");

// --- Exercise detail: plateau verdict + e1RM chart -------------------------
await page.getByRole("link", { name: "Barbell Bench Press" }).click();
await page.locator("svg.recharts-surface").first().waitFor({ timeout: 15000 });
await pause(900);
await shot("07-exercise-plateau.png");

// --- Profile ----------------------------------------------------------------
await page.getByRole("button", { name: "Profile" }).click();
await page.getByText("Training goal").waitFor();
await pause(700);
await shot("08-profile.png");
await pause(800);
mark("end");

await context.close();
const video = await page.video().path();
fs.copyFileSync(video, path.join(DOCS, "demo-raw.webm"));
fs.rmSync(video);
fs.writeFileSync(path.join(DOCS, "marks.json"), JSON.stringify(marks, null, 2));
await browser.close();
console.log("done", JSON.stringify(marks));
