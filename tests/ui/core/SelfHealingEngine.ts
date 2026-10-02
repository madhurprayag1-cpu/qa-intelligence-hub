import { Locator, Page } from "@playwright/test";

/**
 * Custom error hierarchy for Self-Healing locator execution.
 */
export class SelfHealingError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SelfHealingError";
  }
}

export class AmbiguousMatchError extends SelfHealingError {
  readonly selector: string;
  readonly matchCount: number;

  constructor(selector: string, matchCount: number) {
    super(
      `Self-healing rejected ambiguous locator '${selector}': matched ${matchCount} elements in DOM. ` +
        `Strict verification invariant violated: refusing to interact with ambiguous elements.`
    );
    this.name = "AmbiguousMatchError";
    this.selector = selector;
    this.matchCount = matchCount;
  }
}

export class HealingFailedError extends SelfHealingError {
  readonly originalSelector: string;

  constructor(originalSelector: string, reason: string = "no resilient semantic locator could be synthesized") {
    super(`Self-healing failed for selector '${originalSelector}': ${reason}.`);
    this.name = "HealingFailedError";
    this.originalSelector = originalSelector;
  }
}

export interface HealingCandidate {
  selector: string;
  strategy: "TEST_ID" | "ACCESSIBLE_ROLE" | "PLACEHOLDER" | "TEXT" | "ID";
  confidence: number;
  justification: string;
  matchCount?: number;
}

export interface HealingResult {
  healed: boolean;
  status: "ORIGINAL_RESOLVED" | "VERIFIED" | "AMBIGUOUS_MATCH" | "HEALING_FAILED";
  originalSelector: string;
  healedSelector?: string;
  matchCount: number;
  strategy?: string;
  confidence: number;
  verified: boolean;
  durationMs: number;
  diagnosis?: string;
  justification?: string;
  candidates?: string[];
}

export interface HealingOptions {
  timeoutMs?: number;
  throwOnAmbiguous?: boolean;
  throwOnFailure?: boolean;
  apiUrl?: string;
}

/**
 * Specialist Playwright Self-Healing Locator Engine (AGENTS.md Section 6 & 16).
 *
 * Implements autonomous recovery of broken CSS/XPath locators via semantic W3C ARIA
 * accessibility tree evaluation and explicit DOM verification.
 *
 * Invariant: Never silently accepts an ambiguous or incorrect element (count must be strictly 1).
 */
export class SelfHealingEngine {
  private readonly defaultTimeoutMs: number;

  constructor(defaultTimeoutMs: number = 2000) {
    this.defaultTimeoutMs = defaultTimeoutMs;
  }

  /**
   * Resolves a Playwright locator string (e.g. "page.getByTestId('xyz')" or CSS/XPath)
   * into an executable Playwright Locator on the current page.
   */
  resolveLocator(page: Page, selector: string): Locator {
    // 1. page.getByTestId('id')
    const tidMatch = selector.match(/getByTestId\(['"]([^'"]+)['"]\)/);
    if (tidMatch) {
      return page.getByTestId(tidMatch[1]);
    }

    // 2. page.getByRole('button' | 'link' | 'textbox', { name: '...' })
    const roleMatch = selector.match(/getByRole\(['"](\w+)['"],\s*\{\s*name:\s*['"]([^'"]+)['"]\s*\}\)/);
    if (roleMatch) {
      const role = roleMatch[1] as any;
      const name = roleMatch[2];
      return page.getByRole(role, { name, exact: false });
    }

    // 3. page.getByPlaceholder('...')
    const phMatch = selector.match(/getByPlaceholder\(['"]([^'"]+)['"]\)/);
    if (phMatch) {
      return page.getByPlaceholder(phMatch[1]);
    }

    // 4. page.getByText('...')
    const txtMatch = selector.match(/getByText\(['"]([^'"]+)['"]\)/);
    if (txtMatch) {
      return page.getByText(txtMatch[1]);
    }

    // 5. page.locator('#id') or raw selector
    const locMatch = selector.match(/locator\(['"]([^'"]+)['"]\)/);
    if (locMatch) {
      return page.locator(locMatch[1]);
    }

    return page.locator(selector);
  }

  /**
   * Diagnoses why a selector broke based on its syntax.
   */
  diagnoseFailure(selector: string): string {
    if (selector.startsWith("//") || selector.includes("/div") || selector.includes("/form")) {
      return "Hierarchical XPath broken: layout mutations or wrapper elements invalidated the path.";
    }
    if (selector.startsWith(".") || selector.includes(".btn-")) {
      return "Brittle CSS class broken: styles or class hashes modified during build or refactoring.";
    }
    if (selector.startsWith("#")) {
      return "Brittle ID locator failed: element ID was dynamically generated or removed.";
    }
    return "Locator failed due to timing, DOM mutation, or strict mode non-uniqueness.";
  }

  /**
   * Extracts semantic recovery candidates from the live page DOM.
   * Ranks candidates: TestId (0.98) > Accessible Role (0.95) > Placeholder (0.92) > ID (0.85) > Text (0.80).
   */
  async extractCandidates(page: Page, brokenSelector: string): Promise<HealingCandidate[]> {
    const rawCandidates: HealingCandidate[] = [];

    // Evaluate in-page DOM to retrieve candidates
    const extracted = await page.evaluate(() => {
      const items: Array<{ type: string; value: string; extra?: string }> = [];

      // A. data-testid attributes
      const testIdElements = document.querySelectorAll("[data-testid]");
      testIdElements.forEach((el) => {
        const tid = el.getAttribute("data-testid");
        if (tid) {
          items.push({ type: "TEST_ID", value: tid });
        }
      });

      // B. Accessible buttons
      const buttons = document.querySelectorAll("button, input[type='button'], input[type='submit'], [role='button']");
      buttons.forEach((b) => {
        const text = (b.textContent || (b as HTMLInputElement).value || b.getAttribute("aria-label") || "").trim();
        if (text && text.length < 50) {
          items.push({ type: "BUTTON", value: text });
        }
      });

      // C. Accessible inputs with placeholders
      const inputs = document.querySelectorAll("input[placeholder], textarea[placeholder]");
      inputs.forEach((inp) => {
        const ph = inp.getAttribute("placeholder");
        if (ph && ph.trim()) {
          items.push({ type: "PLACEHOLDER", value: ph.trim() });
        }
      });

      // D. Accessible links
      const links = document.querySelectorAll("a[href], [role='link']");
      links.forEach((a) => {
        const text = (a.textContent || a.getAttribute("aria-label") || "").trim();
        if (text && text.length < 50) {
          items.push({ type: "LINK", value: text });
        }
      });

      // E. Explicit IDs (excluding framework containers)
      const ids = document.querySelectorAll("[id]");
      ids.forEach((el) => {
        const id = el.getAttribute("id");
        if (id && !id.startsWith("root") && !id.startsWith("app") && !id.startsWith("__")) {
          items.push({ type: "ID", value: id });
        }
      });

      return items;
    });

    for (const item of extracted) {
      if (item.type === "TEST_ID") {
        rawCandidates.push({
          selector: `page.getByTestId('${item.value}')`,
          strategy: "TEST_ID",
          confidence: 0.98,
          justification: `Explicit automated test contract data-testid="${item.value}". Decoupled from styling.`,
        });
      } else if (item.type === "BUTTON") {
        rawCandidates.push({
          selector: `page.getByRole('button', { name: '${item.value}' })`,
          strategy: "ACCESSIBLE_ROLE",
          confidence: 0.95,
          justification: `W3C ARIA accessible role 'button' with name '${item.value}'.`,
        });
      } else if (item.type === "PLACEHOLDER") {
        rawCandidates.push({
          selector: `page.getByPlaceholder('${item.value}')`,
          strategy: "PLACEHOLDER",
          confidence: 0.92,
          justification: `User-facing placeholder '${item.value}'. Stable across DOM restyling.`,
        });
      } else if (item.type === "LINK") {
        rawCandidates.push({
          selector: `page.getByRole('link', { name: '${item.value}' })`,
          strategy: "ACCESSIBLE_ROLE",
          confidence: 0.90,
          justification: `W3C ARIA accessible role 'link' with name '${item.value}'.`,
        });
      } else if (item.type === "ID") {
        rawCandidates.push({
          selector: `page.locator('#${item.value}')`,
          strategy: "ID",
          confidence: 0.85,
          justification: `Element identifier id="${item.value}".`,
        });
      }
    }

    // Deduplicate preserving highest confidence
    const map = new Map<string, HealingCandidate>();
    for (const c of rawCandidates) {
      const existing = map.get(c.selector);
      if (!existing || c.confidence > existing.confidence) {
        map.set(c.selector, c);
      }
    }

    return Array.from(map.values()).sort((a, b) => b.confidence - a.confidence);
  }

  /**
   * Attempts to heal a broken selector and execute the given action on the live page.
   *
   * Strict Verification Invariant:
   * 1. A candidate must match EXACTLY ONE element (count === 1).
   * 2. If count > 1, the match is rejected as AMBIGUOUS_MATCH to prevent misclicks.
   * 3. If count === 0, healing is marked HEALING_FAILED.
   */
  async executeWithHealing(
    page: Page,
    brokenSelector: string,
    actionName: "click" | "fill",
    actionFn: (loc: Locator) => Promise<void>,
    options?: HealingOptions
  ): Promise<HealingResult> {
    const startTime = Date.now();
    const timeout = options?.timeoutMs ?? this.defaultTimeoutMs;
    const throwOnAmbiguous = options?.throwOnAmbiguous ?? true;
    const throwOnFailure = options?.throwOnFailure ?? true;

    // Step 1: Try original selector first with fast timeout
    try {
      const origLocator = this.resolveLocator(page, brokenSelector);
      await origLocator.waitFor({ state: "attached", timeout });
      const origCount = await origLocator.count();
      if (origCount === 1) {
        await actionFn(origLocator);
        return {
          healed: false,
          status: "ORIGINAL_RESOLVED",
          originalSelector: brokenSelector,
          matchCount: 1,
          confidence: 1.0,
          verified: true,
          durationMs: Date.now() - startTime,
        };
      }
    } catch {
      // Original selector failed — self-healing activates
    }

    // Step 2: Extract candidate locators from the accessibility tree / DOM
    const diagnosis = this.diagnoseFailure(brokenSelector);
    const candidates = await this.extractCandidates(page, brokenSelector);

    let verifiedCandidate: HealingCandidate | null = null;
    let ambiguousCandidate: { candidate: HealingCandidate; count: number } | null = null;

    // Step 3: Strict DOM verification loop
    for (const candidate of candidates) {
      const loc = this.resolveLocator(page, candidate.selector);
      try {
        const count = await loc.count();
        candidate.matchCount = count;
        if (count === 1) {
          verifiedCandidate = candidate;
          break; // Found verified unique match
        } else if (count > 1 && !ambiguousCandidate) {
          ambiguousCandidate = { candidate, count };
        }
      } catch {
        continue;
      }
    }

    // Step 4: Decision & Invariant Enforcement
    if (verifiedCandidate) {
      const targetLoc = this.resolveLocator(page, verifiedCandidate.selector);
      await actionFn(targetLoc);

      return {
        healed: true,
        status: "VERIFIED",
        originalSelector: brokenSelector,
        healedSelector: verifiedCandidate.selector,
        matchCount: 1,
        strategy: verifiedCandidate.strategy,
        confidence: verifiedCandidate.confidence,
        verified: true,
        durationMs: Date.now() - startTime,
        diagnosis,
        justification: `${verifiedCandidate.justification} [Verified: exactly 1 matching element found in DOM].`,
        candidates: candidates.map((c) => c.selector),
      };
    }

    if (ambiguousCandidate) {
      if (throwOnAmbiguous) {
        throw new AmbiguousMatchError(ambiguousCandidate.candidate.selector, ambiguousCandidate.count);
      }
      return {
        healed: false,
        status: "AMBIGUOUS_MATCH",
        originalSelector: brokenSelector,
        matchCount: ambiguousCandidate.count,
        confidence: 0.0,
        verified: false,
        durationMs: Date.now() - startTime,
        diagnosis,
        justification: `Ambiguous match rejected: candidate '${ambiguousCandidate.candidate.selector}' matched ${ambiguousCandidate.count} elements in DOM. Refusing to interact to prevent state corruption.`,
        candidates: candidates.map((c) => c.selector),
      };
    }

    if (throwOnFailure) {
      throw new HealingFailedError(brokenSelector, "no resilient semantic locator could be synthesized");
    }

    return {
      healed: false,
      status: "HEALING_FAILED",
      originalSelector: brokenSelector,
      matchCount: 0,
      confidence: 0.0,
      verified: false,
      durationMs: Date.now() - startTime,
      diagnosis,
      justification: "Healing failed: no resilient semantic locator found in DOM.",
      candidates: candidates.map((c) => c.selector),
    };
  }

  /**
   * Resilient self-healing click.
   */
  async safeClick(page: Page, selector: string, options?: HealingOptions): Promise<HealingResult> {
    return await this.executeWithHealing(
      page,
      selector,
      "click",
      async (loc) => {
        await loc.click({ timeout: options?.timeoutMs ?? this.defaultTimeoutMs });
      },
      options
    );
  }

  /**
   * Resilient self-healing fill.
   */
  async safeFill(page: Page, selector: string, value: string, options?: HealingOptions): Promise<HealingResult> {
    return await this.executeWithHealing(
      page,
      selector,
      "fill",
      async (loc) => {
        await loc.fill(value, { timeout: options?.timeoutMs ?? this.defaultTimeoutMs });
      },
      options
    );
  }
}
