import { test, expect } from "@playwright/test";

test("desktop: investigate contamination and conflicting certificates with real API records", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.getByRole("button", { name: "Sign in to workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Operations overview" }),
  ).toBeVisible();
  await expect(page.getByText("60", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Incidents", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Incidents", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Open", exact: true }).first().click();
  await expect(
    page.getByRole("img", { name: "Supply chain traceability graph" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "RM-042", exact: true }).click();
  await expect(page.getByText("lot:25", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: /Start investigation|Open investigation/ })
    .click();
  await expect(
    page.getByRole("heading", { name: "Investigation workspace" }),
  ).toBeVisible();
  await expect(page.getByText("5 / 5 stages completed")).toBeVisible();
  await expect(
    page.getByText(/No inspection record for PB-003/, { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/4,800 potentially exposed units/)).toBeVisible();
  const downloadEvent = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download report" }).click();
  const downloaded = await downloadEvent;
  expect(downloaded.suggestedFilename()).toMatch(/traceback-\d+\.pdf/);
  const pending = page
    .getByPlaceholder(
      "Explain the evidence supporting your decision (required)",
    )
    .first();
  if (await pending.isVisible()) {
    await pending.fill(
      "Browser QA: simulated hold pending source verification.",
    );
    await page
      .getByRole("button", { name: "Approve simulated action" })
      .first()
      .click();
    await expect(page.getByRole("status")).toContainText("Decision recorded");
  }
  await page.goto("/incidents/2");
  await page
    .getByRole("button", { name: /Start investigation|Open investigation/ })
    .click();
  await expect(page.getByText("5 / 5 stages completed")).toBeVisible();
  await expect(
    page
      .getByText(/contradictory microbiology results; timestamps alone/, {
        exact: false,
      })
      .first(),
  ).toBeVisible();
  await page.goto("/documents");
  await page.getByRole("textbox", { name: "Search documents" }).fill("PB-012");
  await expect(
    page.getByText("PB-012-conflicting-certificate.pdf"),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /PB-012-conflicting-certificate.pdf/ })
    .click();
  await expect(
    page.getByRole("heading", { name: "PB-012-conflicting-certificate.pdf" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Latest agent activity" }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/dashboard-desktop.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("mobile: navigation, incident creation and theme remain usable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Sign in to workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Operations overview" }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBe(true);
  await page.getByRole("button", { name: "Toggle theme" }).click();
  await page.getByRole("button", { name: "Toggle menu" }).click();
  await page.getByRole("link", { name: "Incidents", exact: true }).click();
  await page.getByRole("button", { name: "Report incident" }).click();
  await page.getByLabel("Incident title").fill("Mobile QA incident report");
  await page
    .getByLabel("Description", { exact: true })
    .fill("Created through the real mobile incident form for QA verification.");
  await page
    .getByRole("button", { name: "Create incident", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Mobile QA incident report" }),
  ).toBeVisible();
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Latest agent activity" }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/dashboard-mobile.png",
    fullPage: true,
  });
});

test("all modules, missing-record handling and secure browser sessions", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Sign in to workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Operations overview" }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => sessionStorage.getItem("traceback-token")),
  ).toBeNull();
  expect(await page.evaluate(() => document.cookie)).not.toContain(
    "traceback_session",
  );
  for (const [route, heading] of [
    ["suppliers", "Suppliers"],
    ["lots", "Material lots"],
    ["batches", "Production batches"],
    ["customers", "Customers"],
    ["inspections", "Quality inspections"],
    ["shipments", "Shipments"],
    ["agents", "Agent activity"],
    ["audit", "Audit history"],
    ["investigations", "Investigation center"],
    ["analytics", "Risk & impact analytics"],
    ["reports", "Investigation reports"],
    ["proposals", "Approval center"],
    ["settings", "Workspace settings"],
  ]) {
    await page.goto(`/${route}`);
    await expect(
      page.getByRole("heading", { name: heading, exact: true }),
    ).toBeVisible();
  }
  await page.goto("/incidents/999999");
  await expect(page.getByRole("alert")).toContainText("Record not found");
  await page.getByRole("link", { name: "Return to incidents" }).click();
  await expect(
    page.getByRole("heading", { name: "Incidents", exact: true }),
  ).toBeVisible();
});

test("manufacturing entry forms persist validated records", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Sign in to workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Operations overview" }),
  ).toBeVisible();
  await page.goto("/suppliers");
  await page.getByRole("button", { name: "Add record" }).click();
  const name = `QA Supplier ${Date.now()}`;
  await page.getByLabel("Name", { exact: true }).fill(name);
  await page.getByRole("button", { name: "Save validated record" }).click();
  await expect(page.getByRole("cell", { name, exact: true })).toBeVisible();
});
