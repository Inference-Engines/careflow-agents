import { test, expect } from '@playwright/test';

test.describe('CareFlow E2E Tests', () => {

  // 1. Dashboard loads with real data
  test('Dashboard loads patient data', async ({ page }) => {
    await page.goto('/');
    // Greeting always appears first
    await expect(page.locator('text=Namaste')).toBeVisible({ timeout: 20000 });
    // Wait for any vital data to render (BP or glucose value)
    await expect(page.locator('text=/Elevated|Normal|Near Target/').first()).toBeVisible({ timeout: 30000 });
  });

  // 2. Navigation works
  test('Can navigate between views', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);
    await page.locator('nav >> text=Schedule').first().click();
    await expect(page.locator('text=/Appointment|예정/').first()).toBeVisible({ timeout: 10000 });
    await page.locator('nav >> text=/Doctor/').first().click();
    await expect(page.locator('text=Rajesh Sharma')).toBeVisible({ timeout: 10000 });
  });

  // 3. Dark mode toggle
  test('Dark mode toggles', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);
    await page.locator('button:has-text("Settings"), button:has-text("설정")').first().click();
    await page.waitForTimeout(1000);
    await page.locator('button.rounded-full.w-11').first().click();
    await page.waitForTimeout(500);
    const isDark = await page.locator('html').evaluate(el => el.classList.contains('dark'));
    expect(isDark).toBe(true);
  });

  // 4. Language switching
  test('Language switches to Korean', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);
    await page.locator('button:has-text("Settings"), button:has-text("설정")').first().click();
    await page.waitForTimeout(1000);
    await page.locator('select').first().selectOption('ko');
    await page.waitForTimeout(1000);
    await page.locator('button:has-text("Close"), button:has-text("닫기")').first().click();
    await page.waitForTimeout(500);
    await expect(page.locator('text=홈').first()).toBeVisible({ timeout: 5000 });
  });

  // 5. Chat sends message and gets response
  test('Chat sends message and receives response', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);
    await page.locator('text=/How am I doing/').first().click();
    await expect(page.locator('.prose').first()).toBeVisible({ timeout: 120000 });
    const text = await page.locator('.prose').first().textContent();
    expect(text!.length).toBeGreaterThan(10);
  });

  // 6. AlloyDB data endpoints work
  test('API returns real AlloyDB data', async ({ request }) => {
    const health = await request.get('http://localhost:8001/api/health');
    expect(health.ok()).toBeTruthy();

    const meds = await request.get('http://localhost:8001/api/medications/active?patient_id=11111111-1111-1111-1111-111111111111');
    expect(meds.ok()).toBeTruthy();
    const medsData = await meds.json();
    expect(medsData.data.length).toBeGreaterThan(0);
    const names = medsData.data.map((m: any) => m.name);
    expect(names).toContain('Metformin');

    const appts = await request.get('http://localhost:8001/api/appointments?patient_id=11111111-1111-1111-1111-111111111111');
    expect(appts.ok()).toBeTruthy();
  });

  // 7. MCP SSE server health
  test('MCP SSE server is healthy', async ({ request }) => {
    const health = await request.get('http://localhost:9000/health');
    expect(health.ok()).toBeTruthy();
    const data = await health.json();
    expect(data.tools).toContain('gmail_send');
    expect(data.tools).toContain('calendar_create_event');
    expect(data.oauth_token_exists).toBe(true);
  });

  // 8. Schedule view shows appointments
  test('Schedule shows real appointments', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);
    await page.locator('nav >> text=Schedule').first().click();
    // Wait longer for data load + check for any appointment indicator
    await expect(page.locator('text=/Upcoming|HbA1c|Apollo|Dr\\./').first()).toBeVisible({ timeout: 30000 });
  });

  // 9. Doctor view loads
  test('Doctor view shows pre-visit summary', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);
    await page.locator('nav >> text=/Doctor/').first().click();
    await expect(page.locator('text=Rajesh Sharma')).toBeVisible({ timeout: 10000 });
  });

  // 10. Add custom consult topic
  test('Can add custom consult topic', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);
    await page.locator('nav >> text=/Doctor/').first().click();
    // Wait for Doctor view to fully render
    await expect(page.locator('text=Rajesh Sharma')).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(2000);
    // Scroll down and click the add button
    // Click the dashed add-topic button (first one on the page)
    const addBtn = page.locator('button:has-text("Add Custom"), button:has-text("상담 주제 추가")').first();
    await addBtn.scrollIntoViewIfNeeded();
    await addBtn.click({ timeout: 10000 });
    await page.waitForTimeout(2000);
    // Fill the input in the modal
    const input = page.locator('input[type="text"]');
    await expect(input).toBeVisible({ timeout: 5000 });
    await input.fill('Discuss sleep quality');
    // Press Enter to submit (more reliable than finding the button)
    await input.press('Enter');
    await page.waitForTimeout(2000);
    await expect(page.locator('text=Discuss sleep quality')).toBeVisible({ timeout: 15000 });
  });
});
