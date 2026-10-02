import json
import pytest
from agents import UIHealingAgent
from mcp_server import call_tool, list_tools


def test_heal_xpath_to_accessible_button_role():
    """
    Validates healing a fragile hierarchical XPath into a W3C ARIA accessible role locator.
    """
    agent = UIHealingAgent()
    dom_snippet = """
    <div class="search-form-container">
        <form>
            <div class="row"><input type="text" value="ATH" /></div>
            <div class="actions">
                <button type="submit" class="btn btn-primary btn-lg">Search Flights</button>
            </div>
        </form>
    </div>
    """
    result = agent.heal_selector(
        broken_selector="//div[2]/form/div[3]/button[1]",
        dom_snippet=dom_snippet,
        failure_message="TimeoutError: locator.click: Timeout 5000ms exceeded waiting for locator('//div[2]/form/div[3]/button[1]')",
        target_action="click",
    )

    assert result["healed_selector"] == "page.getByRole('button', { name: 'Search Flights' })"
    assert result["confidence_score"] >= 0.95
    assert result["resilience_rating"] == "HIGH"
    assert "XPath" in result["diagnosis"]
    assert "await page.getByRole('button', { name: 'Search Flights' }).click();" in result["code_replacement"]


def test_heal_broken_class_to_testid():
    """
    Validates healing a broken CSS class name to an explicit data-testid test contract.
    """
    agent = UIHealingAgent()
    dom_snippet = """
    <div class="payment-modal">
        <button class="legacy-btn-v2024 active" data-testid="confirm-booking-btn">
            Confirm &amp; Pay
        </button>
    </div>
    """
    result = agent.heal_selector(
        broken_selector=".legacy-btn-v2024",
        dom_snippet=dom_snippet,
        target_action="click",
    )

    assert result["healed_selector"] == "page.getByTestId('confirm-booking-btn')"
    assert result["confidence_score"] >= 0.98
    assert result["resilience_rating"] == "HIGH"
    assert "CSS" in result["diagnosis"]
    assert "page.getByRole('button', { name: 'Confirm &amp; Pay' })" in result["alternatives"]


def test_heal_input_placeholder():
    """
    Validates healing an input locator by targeting placeholder attribute.
    """
    agent = UIHealingAgent()
    dom_snippet = """
    <div class="input-field">
        <input id="origin-dynamic-12345" type="text" placeholder="Origin Airport (e.g. ATH)" />
    </div>
    """
    result = agent.heal_selector(
        broken_selector="#origin-dynamic-12345",
        dom_snippet=dom_snippet,
        target_action="fill('ATH')",
    )

    assert result["healed_selector"] == "page.getByPlaceholder('Origin Airport (e.g. ATH)')"
    assert result["confidence_score"] >= 0.92
    assert result["resilience_rating"] == "HIGH"


@pytest.mark.anyio
async def test_ui_healing_agent_async_execution():
    """
    Validates end-to-end async execution of UIHealingAgent with event generation.
    """
    agent = UIHealingAgent()
    dom_snippet = '<button data-testid="login-submit">Sign In</button>'
    run = await agent.execute(
        task="Heal broken login button locator",
        context={
            "broken_selector": "//button[@class='btn-signin']",
            "dom_snippet": dom_snippet,
            "target_action": "click",
        },
    )

    assert run.status == "COMPLETED"
    assert any(e.event_type == "SELECTOR_HEALED" for e in run.events)
    output_data = json.loads(run.output)
    assert output_data["healed_selector"] == "page.getByTestId('login-submit')"


def test_heal_playwright_selector_mcp_tool():
    """
    Validates MCP tool registry and invocation for heal_playwright_selector.
    """
    tools = list_tools()
    assert any(t["name"] == "heal_playwright_selector" for t in tools)

    resp = call_tool(
        "heal_playwright_selector",
        {
            "broken_selector": "//div[1]/form/button",
            "dom_snippet": '<button data-testid="submit-pax">Proceed to Payment</button>',
            "target_action": "click",
        },
    )

    assert resp["status"] == "success"
    assert resp["tool"] == "heal_playwright_selector"
    assert resp["result"]["healed_selector"] == "page.getByTestId('submit-pax')"
    assert resp["latency_ms"] >= 0


def test_heal_selector_verified_unique_status():
    """
    Validates that a uniquely matching element in the DOM is verified and accepted.
    """
    agent = UIHealingAgent()
    dom_snippet = """
    <div class="booking-summary">
        <button data-testid="complete-checkout" class="btn btn-primary">Complete Checkout</button>
    </div>
    """
    result = agent.heal_selector(
        broken_selector="#btn-checkout-v1",
        dom_snippet=dom_snippet,
        failure_message="TimeoutError: element not found",
        target_action="click",
    )

    assert result["status"] == "VERIFIED"
    assert result["verified"] is True
    assert result["match_count"] == 1
    assert result["healed_selector"] == "page.getByTestId('complete-checkout')"
    assert result["confidence_score"] >= 0.95
    assert "Verified: exactly 1 matching element found" in result["justification"]


def test_heal_selector_rejects_ambiguous_matches():
    """
    Validates that when multiple elements match a candidate locator in the DOM,
    the self-healing engine strictly refuses to silently select an arbitrary element,
    flagging AMBIGUOUS_MATCH and setting verified=False.
    """
    agent = UIHealingAgent()
    # Two identical buttons without unique testids or distinguishing text
    dom_snippet = """
    <div class="passenger-list">
        <div class="pax-row">
            <button class="btn-action">Cancel Reservation</button>
        </div>
        <div class="pax-row">
            <button class="btn-action">Cancel Reservation</button>
        </div>
    </div>
    """
    result = agent.heal_selector(
        broken_selector=".btn-action.pax-target-1",
        dom_snippet=dom_snippet,
        failure_message="Timeout waiting for .btn-action.pax-target-1",
        target_action="click",
    )

    assert result["status"] == "AMBIGUOUS_MATCH"
    assert result["verified"] is False
    assert result["match_count"] == 2
    assert result["healed_selector"] is None
    assert result["confidence_score"] == 0.0
    assert result["resilience_rating"] == "UNSAFE"
    assert "Ambiguous match rejected" in result["justification"]
    assert "refused to interact" in result["justification"]


def test_heal_selector_failed_unrecoverable():
    """
    Validates that when no resilient semantic candidates can be identified in the DOM,
    the engine returns HEALING_FAILED with verified=False and 0 confidence.
    """
    agent = UIHealingAgent()
    dom_snippet = """
    <div class="empty-state-card">
        <!-- No buttons, links, inputs, or actionable elements -->
    </div>
    """
    result = agent.heal_selector(
        broken_selector="#missing-ghost-button",
        dom_snippet=dom_snippet,
        failure_message="Timeout waiting for #missing-ghost-button",
        target_action="click",
    )

    assert result["status"] == "HEALING_FAILED"
    assert result["verified"] is False
    assert result["match_count"] == 0
    assert result["healed_selector"] is None
    assert result["confidence_score"] == 0.0
    assert result["resilience_rating"] == "NONE"
    assert "Healing failed" in result["justification"]


@pytest.mark.anyio
async def test_ui_healing_agent_async_ambiguous_rejection():
    """
    Validates async execution of UIHealingAgent when ambiguous matches are detected,
    ensuring HEALING_AMBIGUOUS_REJECTED event is emitted and status is REJECTED.
    """
    agent = UIHealingAgent()
    dom_snippet = """
    <div>
        <button>Select Seat</button>
        <button>Select Seat</button>
        <button>Select Seat</button>
    </div>
    """
    run = await agent.execute(
        task="Heal broken seat selection button",
        context={
            "broken_selector": "#seat-btn-row-12",
            "dom_snippet": dom_snippet,
            "target_action": "click",
        },
    )

    assert run.status == "REJECTED"
    assert any(e.event_type == "HEALING_AMBIGUOUS_REJECTED" for e in run.events)
    output = json.loads(run.output)
    assert output["status"] == "AMBIGUOUS_MATCH"
    assert output["verified"] is False
    assert output["match_count"] == 3


def test_count_matches_helper_locators():
    """
    Validates count_matches across different locator syntax families.
    """
    agent = UIHealingAgent()
    snippet = """
    <div>
        <button data-testid="pax-save">Save</button>
        <button>Confirm Booking</button>
        <a href="/faq">Help Center</a>
        <input placeholder="Flight Number (e.g. QA-101)" id="flight-num-inp" />
    </div>
    """
    assert agent.count_matches("page.getByTestId('pax-save')", snippet) == 1
    assert agent.count_matches("page.getByTestId('non-existent')", snippet) == 0
    assert agent.count_matches("page.getByRole('button', { name: 'Confirm Booking' })", snippet) == 1
    assert agent.count_matches("page.getByRole('link', { name: 'Help Center' })", snippet) == 1
    assert agent.count_matches("page.getByPlaceholder('Flight Number (e.g. QA-101)')", snippet) == 1
    assert agent.count_matches("page.locator('#flight-num-inp')", snippet) == 1
