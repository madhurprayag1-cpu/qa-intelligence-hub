import React, { useEffect, useState } from "react";
import {
  createTelecomSubscriber,
  executeTelecomSimSwap,
  fetchTelecomPlans,
  fetchTelecomSubscriber,
  fetchTelecomSubscriberCDRs,
  rateTelecomCDR,
  updateTelecomSubscriberStatus,
} from "../api";
import type {
  CallDetailRecord,
  RateCDRResponse,
  TelecomPlan,
  TelecomSubscriber,
} from "../types";

export function TelecomView() {
  // State: Plans & Selection
  const [plans, setPlans] = useState<TelecomPlan[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string>("PLAN-5G-UNLIMITED");

  // State: Subscriber Provisioning
  const [msisdn, setMsisdn] = useState("+1-555-010-0042");
  const [iccid, setIccid] = useState("89014103211118510720");
  const [imsi, setImsi] = useState("310410123456789");
  const [balance, setBalance] = useState("50.00");
  const [roamingAllowed, setRoamingAllowed] = useState(true);
  const [activeSubscriber, setActiveSubscriber] = useState<TelecomSubscriber | null>(null);

  // State: CPNI & Lifecycle
  const [targetSubStatus, setTargetSubStatus] = useState("ACTIVE");
  const [cpniDefect, setCpniDefect] = useState<string>("");
  const [lifecycleDefect, setLifecycleDefect] = useState<string>("");

  // State: SIM Swap
  const [swapMsisdn, setSwapMsisdn] = useState("+1-555-010-0042");
  const [swapNewIccid, setSwapNewIccid] = useState("89014103299998510999");
  const [swapNewImsi, setSwapNewImsi] = useState("310410999999999");
  const [swapDefect, setSwapDefect] = useState<string>("");
  const [swapResult, setSwapResult] = useState<{
    status: string;
    new_iccid?: string;
    old_iccid_deactivated?: boolean;
    twin_sim_active?: boolean;
  } | null>(null);

  // State: CDR Generation & Rating
  const [cdrCallType, setCdrCallType] = useState("DATA");
  const [cdrDestination, setCdrDestination] = useState("+1-555-019-9999");
  const [cdrDurationSec, setCdrDurationSec] = useState("120");
  const [cdrBytes, setCdrBytes] = useState("52428800"); // 50 MB
  const [cdrZone, setCdrZone] = useState("DOMESTIC");
  const [cdrDefect, setCdrDefect] = useState<string>("");
  const [lastRatedCDR, setLastRatedCDR] = useState<RateCDRResponse | null>(null);
  const [cdrList, setCdrList] = useState<CallDetailRecord[]>([]);

  // Status & Feedback
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadPlans = async () => {
    try {
      const p = await fetchTelecomPlans();
      setPlans(p);
      if (p.length > 0) {
        setSelectedPlanId(p[0].plan_id);
      }
    } catch {
      // Hermetic fallback
    }
  };

  const loadSubscriberCDRs = async (targetMsisdn: string) => {
    try {
      const cdrs = await fetchTelecomSubscriberCDRs(targetMsisdn);
      setCdrList(cdrs);
    } catch {
      setCdrList([]);
    }
  };

  useEffect(() => {
    let isMounted = true;
    fetchTelecomPlans()
      .then((p) => {
        if (!isMounted) return;
        setPlans(p);
        if (p.length > 0) {
          setSelectedPlanId(p[0].plan_id);
        }
      })
      .catch(() => {});

    return () => {
      isMounted = false;
    };
  }, []);

  // 1. Provision Subscriber Line
  const handleProvisionSubscriber = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const chosenPlan = plans.find((p) => p.plan_id === selectedPlanId) || {
        plan_id: selectedPlanId,
        name: "5G Unlimited Enterprise",
        plan_type: "enterprise",
        monthly_fee: 75.0,
        voice_minutes_included: 5000,
        sms_included: 5000,
        data_gb_included: 100,
        fup_threshold_gb: 100,
        overage_voice_per_min: 0.05,
        overage_data_per_mb: 0.01,
        roaming_enabled: true,
        throttle_speed_kbps: 128,
      };

      const cleanDigits = msisdn.replace(/\D/g, "");
      const subscriberId = cleanDigits
        ? `SUB-${cleanDigits}`
        : `SUB-${Date.now().toString().slice(-6)}`;

      const newSubscriber: TelecomSubscriber = {
        subscriber_id: subscriberId,
        msisdn,
        sim: {
          iccid,
          imsi,
          is_esim: false,
          is_active: true,
          puk_code: "12345678",
        },
        plan: chosenPlan,
        status: "active",
        balance: parseFloat(balance) || 50.0,
        roaming_allowed: roamingAllowed,
      };

      const res = await createTelecomSubscriber(newSubscriber);
      setActiveSubscriber(res);
      setSwapMsisdn(res.msisdn);
      setSuccessMsg(
        `Subscriber line ${res.msisdn} provisioned successfully on ${res.plan.name} ($${res.balance.toFixed(2)} balance).`
      );
      loadSubscriberCDRs(res.msisdn);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Subscriber provisioning failed"
      );
    } finally {
      setLoading(false);
    }
  };

  // 2. Fetch Profile & CPNI Privacy Verification
  const handleCheckCPNI = async () => {
    if (!activeSubscriber) return;
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const res = await fetchTelecomSubscriber(
        activeSubscriber.msisdn,
        cpniDefect ? cpniDefect : undefined
      );
      setActiveSubscriber(res);
      if (res._diagnostic_trace) {
        setSuccessMsg("🚨 CPNI DIAGNOSTIC LEAK: Unmasked IMSI, ICCID, and PUK code exposed in diagnostic response!");
      } else {
        setSuccessMsg("🛡️ CPNI COMPLIANT: MSISDN, IMSI, and PUK code verified strictly masked.");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "CPNI lookup failed");
    } finally {
      setLoading(false);
    }
  };

  // 3. Update Lifecycle Status
  const handleUpdateStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeSubscriber) {
      setError("Provision or select an active subscriber first.");
      return;
    }
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const res = await updateTelecomSubscriberStatus(
        activeSubscriber.msisdn,
        targetSubStatus,
        lifecycleDefect ? lifecycleDefect : undefined
      );
      setActiveSubscriber(res);
      setSuccessMsg(`Subscriber ${res.msisdn} transitioned to status: ${res.status}.`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Status transition failed");
    } finally {
      setLoading(false);
    }
  };

  // 4. SIM / eSIM Swap
  const handleSimSwap = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const res = await executeTelecomSimSwap(
        swapMsisdn,
        { new_iccid: swapNewIccid, new_imsi: swapNewImsi },
        swapDefect ? swapDefect : undefined
      );

      setSwapResult(res);
      if (res.twin_sim_active) {
        setSuccessMsg("🚨 SIM SWAP RACE: Twin SIM cards active simultaneously on subscriber line!");
      } else {
        setSuccessMsg(`SIM Swap Completed for ${swapMsisdn}: Old ICCID deactivated, new ICCID activated.`);
      }

      // Refresh subscriber
      const updated = await fetchTelecomSubscriber(swapMsisdn).catch(() => null);
      if (updated) setActiveSubscriber(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "SIM swap failed");
    } finally {
      setLoading(false);
    }
  };

  // 5. Rate CDR Usage Record
  const handleRateCDR = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeSubscriber) {
      setError("Provision or select a subscriber line first.");
      return;
    }
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const dur = parseInt(cdrDurationSec, 10);
      const bytes = parseInt(cdrBytes, 10);

      const cdrRecord: CallDetailRecord = {
        cdr_id: `CDR-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
        msisdn: activeSubscriber.msisdn,
        destination: cdrDestination,
        call_type: cdrCallType.toLowerCase(),
        zone: cdrZone.toLowerCase(),
        duration_seconds: isNaN(dur) ? 0 : dur,
        bytes_transferred: isNaN(bytes) ? 0 : bytes,
      };

      const res = await rateTelecomCDR(
        cdrRecord,
        cdrDefect ? cdrDefect : undefined
      );

      setLastRatedCDR(res);
      setSuccessMsg(
        `CDR Rated & Billed: $${res.rated_amount.toFixed(2)} charged. Remaining balance: $${res.balance_remaining.toFixed(2)}.`
      );

      // Refresh balance & usage history
      setActiveSubscriber((prev) => (prev ? { ...prev, balance: res.balance_remaining } : prev));
      loadSubscriberCDRs(activeSubscriber.msisdn);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "CDR rating failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="domain-view telecom-view" data-testid="telecom-view">
      {/* Banner */}
      <section className="domain-banner" data-testid="telecom-banner">
        <div className="domain-banner-header">
          <div className="domain-badge-group">
            <span className="domain-pill" style={{ background: "rgba(139, 92, 246, 0.2)", color: "#a78bfa", border: "1px solid rgba(139, 92, 246, 0.4)" }}>
              📡 TELECOM & 5G BSS/OSS SUT
            </span>
            <span className="domain-standard-tag">5G Tariffing • SIM/eSIM Swap • Rating Engine • CPNI Privacy</span>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={loadPlans}
            data-testid="telecom-refresh-btn"
          >
            🔄 Reload Plans
          </button>
        </div>
        <p className="domain-desc">
          Execute realistic Telecom BSS/OSS workflows: 5G tariff plan selection, subscriber line provisioning,
          CPNI privacy masking, SIM/eSIM swaps with anti-cloning checks, real-time CDR usage generation, and rating engine billing.
        </p>
      </section>

      {/* Global Alerts */}
      {error && (
        <div className="alert alert-danger fade-in" role="alert" data-testid="telecom-error-banner">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {successMsg && !error && (
        <div className="alert alert-success fade-in" role="alert" data-testid="telecom-success-banner">
          <span>✅</span>
          <span>{successMsg}</span>
        </div>
      )}

      <div className="domain-grid">
        {/* LEFT COLUMN: 5G Plans & Subscriber Provisioning */}
        <div className="domain-card-column">
          {/* Plan Catalog */}
          <section className="form-card" data-testid="plans-section">
            <div className="card-header-styled">
              <span className="step-num">1</span>
              <div>
                <h3>5G Tariff & Mobile Data Plans</h3>
                <p className="subtext">Select enterprise or consumer subscription plans with allowances</p>
              </div>
            </div>

            <div className="plan-cards-grid mt-2" data-testid="plans-list">
              {plans.map((p) => (
                <div
                  key={p.plan_id}
                  className={`plan-card ${selectedPlanId === p.plan_id ? "selected-plan" : ""}`}
                  onClick={() => setSelectedPlanId(p.plan_id)}
                  data-testid={`plan-card-${p.plan_id}`}
                >
                  <div className="plan-card-top">
                    <strong className="plan-name">{p.name}</strong>
                  <span className="status-badge badge-active">{p.plan_type}</span>
                  </div>
                  <div className="plan-price mt-1">
                    ${p.monthly_fee.toFixed(2)} <span className="text-xs text-secondary">/ month</span>
                  </div>
                  <div className="plan-features text-sm mt-2">
                    <div>📶 <strong>{p.data_gb_included} GB</strong> 5G Data</div>
                    <div>📞 <strong>{p.voice_minutes_included}</strong> Voice Minutes</div>
                    <div>💬 <strong>{p.sms_included}</strong> SMS Allowance</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Line Provisioning Form */}
          <section className="form-card mt-4" data-testid="provisioning-section">
            <div className="card-header-styled">
              <span className="step-num">2</span>
              <div>
                <h3>Subscriber Line Provisioning</h3>
                <p className="subtext">Activate MSISDN with associated SIM ICCID and network IMSI</p>
              </div>
            </div>

            <form onSubmit={handleProvisionSubscriber} data-testid="provision-form">
              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="tc-msisdn">Subscriber Phone (MSISDN)</label>
                  <input
                    id="tc-msisdn"
                    type="text"
                    value={msisdn}
                    onChange={(e) => setMsisdn(e.target.value)}
                    required
                    data-testid="input-msisdn"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="tc-balance">Initial Prepaid Balance ($)</label>
                  <input
                    id="tc-balance"
                    type="number"
                    step="5"
                    value={balance}
                    onChange={(e) => setBalance(e.target.value)}
                    required
                    data-testid="input-subscriber-balance"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="tc-iccid">SIM Card ICCID (20 digits)</label>
                  <input
                    id="tc-iccid"
                    type="text"
                    value={iccid}
                    onChange={(e) => setIccid(e.target.value)}
                    required
                    data-testid="input-iccid"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="tc-imsi">Network IMSI (15 digits)</label>
                  <input
                    id="tc-imsi"
                    type="text"
                    value={imsi}
                    onChange={(e) => setImsi(e.target.value)}
                    required
                    data-testid="input-imsi"
                  />
                </div>
              </div>

              <div className="form-group mt-2">
                <label className="checkbox-label text-sm">
                  <input
                    type="checkbox"
                    checked={roamingAllowed}
                    onChange={(e) => setRoamingAllowed(e.target.checked)}
                    data-testid="checkbox-roaming"
                  />
                  Enable International Roaming Allowance
                </label>
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-block mt-3"
                disabled={loading}
                data-testid="submit-provision-btn"
              >
                {loading ? "Activating..." : "📱 Provision Line on 5G Core"}
              </button>
            </form>

            {/* Active Subscriber Profile Card */}
            {activeSubscriber && (
              <div className="status-box mt-4" data-testid="active-subscriber-card">
                <div className="status-box-header">
                  <span className="status-pill status-pill-online" data-testid="subscriber-msisdn">
                    MSISDN: {activeSubscriber.msisdn}
                  </span>
                  <span className="status-pill status-pill-online" data-testid="subscriber-status">
                    STATUS: {activeSubscriber.status}
                  </span>
                </div>
                <div className="patient-meta-grid mt-2">
                  <div>
                    <span className="meta-label">SIM IMSI:</span>
                    <strong data-testid="subscriber-imsi" style={{ color: "#38bdf8" }}>
                      {activeSubscriber.sim?.imsi || "N/A"}
                    </strong>
                  </div>
                  <div>
                    <span className="meta-label">Available Balance:</span>
                    <strong data-testid="subscriber-balance" style={{ color: "#10b981", fontSize: "16px" }}>
                      ${activeSubscriber.balance.toFixed(2)}
                    </strong>
                  </div>
                  <div>
                    <span className="meta-label">Active Plan:</span>
                    <span>{activeSubscriber.plan?.name}</span>
                  </div>
                  <div>
                    <span className="meta-label">Roaming Status:</span>
                    <span>{activeSubscriber.roaming_allowed ? "ALLOWED" : "BLOCKED"}</span>
                  </div>
                </div>

                {activeSubscriber._diagnostic_trace && (
                  <div className="alert alert-danger mt-3 text-xs" data-testid="cpni-leak-alert">
                    🚨 DEF-TC-006 CPNI LEAK DETECTED: Unmasked IMSI (
                    {String(activeSubscriber._diagnostic_trace.unmasked_imsi)}), ICCID (
                    {String(activeSubscriber._diagnostic_trace.unmasked_iccid)}), and PUK code exposed!
                  </div>
                )}
              </div>
            )}
          </section>
        </div>

        {/* RIGHT COLUMN: SIM Swap, CDR Rating, and CPNI Inspection */}
        <div className="domain-card-column">
          {/* CPNI & Lifecycle Section */}
          <section className="form-card" data-testid="cpni-lifecycle-section">
            <div className="card-header-styled">
              <span className="step-num">3</span>
              <div>
                <h3>CPNI Privacy & Subscription Lifecycle</h3>
                <p className="subtext">Verify privacy masking rules and transition subscriber status</p>
              </div>
            </div>

            <div className="form-row mt-2">
              <div className="form-group flex-1">
                <label htmlFor="tc-status-target">Target Subscription Status</label>
                <select
                  id="tc-status-target"
                  value={targetSubStatus}
                  onChange={(e) => setTargetSubStatus(e.target.value)}
                  data-testid="select-sub-status"
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="SUSPENDED">SUSPENDED</option>
                  <option value="TERMINATED">TERMINATED</option>
                </select>
              </div>
              <div className="form-group flex-1">
                <label htmlFor="tc-lifecycle-defect">QA FSM Defect</label>
                <select
                  id="tc-lifecycle-defect"
                  value={lifecycleDefect}
                  onChange={(e) => setLifecycleDefect(e.target.value)}
                  data-testid="select-lifecycle-defect"
                >
                  <option value="">None (Strict FSM)</option>
                  <option value="DEF-TC-005">
                    DEF-TC-005: Illegal State Transition
                  </option>
                  <option value="INVALID_STATE_TRANSITION">
                    INVALID_STATE_TRANSITION (DEF-TC-005)
                  </option>
                </select>
              </div>
            </div>

            <div className="form-row mt-2">
              <button
                type="button"
                className="btn btn-secondary flex-1"
                onClick={handleUpdateStatus}
                disabled={loading || !activeSubscriber}
                data-testid="submit-transition-btn"
              >
                🔄 Apply State Transition
              </button>
              <button
                type="button"
                className="btn btn-secondary flex-1"
                onClick={handleCheckCPNI}
                disabled={loading || !activeSubscriber}
                data-testid="inspect-cpni-btn"
              >
                🔍 Inspect CPNI Masking
              </button>
            </div>

            <div className="defect-hook-box mt-3">
              <label htmlFor="tc-cpni-defect" className="defect-label">
                🧪 QA CPNI Privacy Defect Hook:
              </label>
              <select
                id="tc-cpni-defect"
                value={cpniDefect}
                onChange={(e) => setCpniDefect(e.target.value)}
                data-testid="select-cpni-defect"
              >
                <option value="">None (Standard CPNI Masking)</option>
                <option value="DEF-TC-006">
                  DEF-TC-006: CDR PII Unmasked Log (Expose full IMSI/PUK in trace)
                </option>
                <option value="DEF-TC-001">
                  DEF-TC-001: CPNI Data Leak (Unmasked IMSI & PUK in trace)
                </option>
                <option value="CDR_PII_UNMASKED_LOG">
                  CDR_PII_UNMASKED_LOG (DEF-TC-006)
                </option>
              </select>
            </div>
          </section>

          {/* SIM / eSIM Swap Engine */}
          <section className="form-card mt-4" data-testid="sim-swap-section">
            <div className="card-header-styled">
              <span className="step-num">4</span>
              <div>
                <h3>SIM / eSIM Swap Engine</h3>
                <p className="subtext">Transfer subscription to new SIM with anti-cloning deactivation</p>
              </div>
            </div>

            <form onSubmit={handleSimSwap} data-testid="sim-swap-form">
              <div className="form-group">
                <label htmlFor="tc-swap-phone">Target Subscriber Phone</label>
                <input
                  id="tc-swap-phone"
                  type="text"
                  value={swapMsisdn}
                  onChange={(e) => setSwapMsisdn(e.target.value)}
                  required
                  data-testid="input-swap-msisdn"
                />
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="tc-swap-iccid">New Replacement ICCID</label>
                  <input
                    id="tc-swap-iccid"
                    type="text"
                    value={swapNewIccid}
                    onChange={(e) => setSwapNewIccid(e.target.value)}
                    required
                    data-testid="input-swap-iccid"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="tc-swap-imsi">New Replacement IMSI</label>
                  <input
                    id="tc-swap-imsi"
                    type="text"
                    value={swapNewImsi}
                    onChange={(e) => setSwapNewImsi(e.target.value)}
                    required
                    data-testid="input-swap-imsi"
                  />
                </div>
              </div>

              {/* Defect injection hook for swap */}
              <div className="defect-hook-box">
                <label htmlFor="tc-swap-defect" className="defect-label">
                  🧪 QA SIM Swap Defect Hook:
                </label>
                <select
                  id="tc-swap-defect"
                  value={swapDefect}
                  onChange={(e) => setSwapDefect(e.target.value)}
                  data-testid="select-swap-defect"
                >
                  <option value="">None (Deactivate Old SIM Immediately)</option>
                  <option value="DEF-TC-001">
                    DEF-TC-001: SIM Swap Race Condition (Leaves both SIMs active simultaneously)
                  </option>
                  <option value="DEF-TC-002">
                    DEF-TC-002: Twin-SIM Concurrency Flaw (Duplicate Activation Warning)
                  </option>
                  <option value="SIM_SWAP_RACE">
                    SIM_SWAP_RACE (DEF-TC-001)
                  </option>
                </select>
              </div>

              <button
                type="submit"
                className="btn btn-secondary btn-block mt-2"
                disabled={loading}
                data-testid="submit-swap-btn"
              >
                {loading ? "Swapping..." : "🔄 Execute SIM / eSIM Swap"}
              </button>
            </form>

            {swapResult && (
              <div className="status-box mt-3" data-testid="swap-result-box">
                <div className="status-box-header">
                  <span className="status-pill status-pill-online" data-testid="sim-swap-status">
                    STATUS: {swapResult.status}
                  </span>
                  <span className={`status-pill ${swapResult.twin_sim_active ? "status-pill-offline" : "status-pill-online"}`}>
                    {swapResult.twin_sim_active ? "🚨 TWIN SIM ACTIVE" : "✅ OLD SIM DEACTIVATED"}
                  </span>
                </div>
              </div>
            )}
          </section>

          {/* CDR Usage Generation & Rating Engine */}
          <section className="form-card mt-4" data-testid="cdr-rating-section">
            <div className="card-header-styled">
              <span className="step-num">5</span>
              <div>
                <h3>Call Detail Record (CDR) Rating & Billing</h3>
                <p className="subtext">Simulate network usage events and calculate tariff charges</p>
              </div>
            </div>

            <form onSubmit={handleRateCDR} data-testid="cdr-rating-form">
              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="tc-cdr-type">Usage Event Type</label>
                  <select
                    id="tc-cdr-type"
                    value={cdrCallType}
                    onChange={(e) => setCdrCallType(e.target.value)}
                    data-testid="select-cdr-type"
                  >
                    <option value="DATA">5G Mobile Data (Bytes)</option>
                    <option value="VOICE">Voice Call (Seconds)</option>
                    <option value="SMS">SMS Message</option>
                    <option value="ROAMING_VOICE">Roaming Voice Call</option>
                    <option value="ROAMING_DATA">Roaming Mobile Data</option>
                  </select>
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="tc-cdr-zone">Rating Zone</label>
                  <select
                    id="tc-cdr-zone"
                    value={cdrZone}
                    onChange={(e) => setCdrZone(e.target.value)}
                    data-testid="select-cdr-zone"
                  >
                    <option value="DOMESTIC">Domestic</option>
                    <option value="INTERNATIONAL">International</option>
                    <option value="PREMIUM">Premium Rate</option>
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="tc-cdr-dest">Destination #</label>
                  <input
                    id="tc-cdr-dest"
                    type="text"
                    value={cdrDestination}
                    onChange={(e) => setCdrDestination(e.target.value)}
                    required
                    data-testid="input-cdr-destination"
                  />
                </div>
                {cdrCallType.includes("DATA") ? (
                  <div className="form-group flex-1">
                    <label htmlFor="tc-cdr-bytes">Bytes (e.g. 52428800 = 50MB)</label>
                    <input
                      id="tc-cdr-bytes"
                      type="number"
                      value={cdrBytes}
                      onChange={(e) => setCdrBytes(e.target.value)}
                      required
                      data-testid="input-cdr-bytes"
                    />
                  </div>
                ) : (
                  <div className="form-group flex-1">
                    <label htmlFor="tc-cdr-dur">Duration (Seconds)</label>
                    <input
                      id="tc-cdr-dur"
                      type="number"
                      value={cdrDurationSec}
                      onChange={(e) => setCdrDurationSec(e.target.value)}
                      required
                      data-testid="input-cdr-duration"
                    />
                  </div>
                )}
              </div>

              {/* Defect injection hook for CDR */}
              <div className="defect-hook-box">
                <label htmlFor="tc-cdr-defect" className="defect-label">
                  🧪 QA Billing Defect Hook:
                </label>
                <select
                  id="tc-cdr-defect"
                  value={cdrDefect}
                  onChange={(e) => setCdrDefect(e.target.value)}
                  data-testid="select-cdr-defect"
                >
                  <option value="">None (Standard Rating Engine)</option>
                  <option value="DEF-TC-002">
                    DEF-TC-002: Fractional MB Overage Miscalculation (Rounds up to full GB)
                  </option>
                  <option value="CDR_OVERAGE_MISCALCULATION">
                    CDR_OVERAGE_MISCALCULATION (DEF-TC-002)
                  </option>
                  <option value="DEF-TC-003">
                    DEF-TC-003: Unauthorized Roaming Usage Leak (Bypass check)
                  </option>
                  <option value="UNAUTHORIZED_ROAMING_LEAK">
                    UNAUTHORIZED_ROAMING_LEAK (DEF-TC-003)
                  </option>
                  <option value="DEF-TC-004">
                    DEF-TC-004: Double Billing Duplicate CDR Race (Bypass deduplication)
                  </option>
                  <option value="DOUBLE_BILLING_CDR_RACE">
                    DOUBLE_BILLING_CDR_RACE (DEF-TC-004)
                  </option>
                </select>
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-block mt-3"
                disabled={loading || !activeSubscriber}
                data-testid="submit-cdr-btn"
              >
                {loading ? "Rating..." : "⚡ Rate CDR & Bill Account"}
              </button>
            </form>

            {/* CDR Rating Result */}
            {lastRatedCDR && (
              <div className="status-box mt-4" data-testid="cdr-result-box">
                <div className="status-box-header">
                  <span className="status-pill status-pill-online" data-testid="cdr-id">
                    CDR: {lastRatedCDR.cdr_id}
                  </span>
                  <span className="status-pill status-pill-online">
                    STATUS: {lastRatedCDR.status}
                  </span>
                </div>
                <div className="patient-meta-grid mt-2">
                  <div>
                    <span className="meta-label">Rated Charge:</span>
                    <strong data-testid="cdr-rated-amount" style={{ fontSize: "16px", color: "#38bdf8" }}>
                      ${lastRatedCDR.rated_amount.toFixed(2)}
                    </strong>
                  </div>
                  <div>
                    <span className="meta-label">Remaining Balance:</span>
                    <strong data-testid="cdr-remaining-balance" style={{ fontSize: "16px", color: "#10b981" }}>
                      ${lastRatedCDR.balance_remaining.toFixed(2)}
                    </strong>
                  </div>
                </div>
              </div>
            )}

            {/* Usage History Table */}
            {cdrList.length > 0 && (
              <div className="mt-4" data-testid="cdr-history-table-wrapper">
                <h4>Subscriber CDR Usage History ({cdrList.length})</h4>
                <div className="table-responsive mt-2">
                  <table className="data-table" data-testid="cdr-history-table">
                    <thead>
                      <tr>
                        <th>CDR ID</th>
                        <th>Type</th>
                        <th>Destination</th>
                        <th>Duration / Data</th>
                        <th>Rated Fee</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cdrList.map((c) => (
                        <tr key={c.cdr_id}>
                          <td><code>{c.cdr_id}</code></td>
                          <td><span className="status-badge badge-active">{c.call_type}</span></td>
                          <td>{c.destination}</td>
                          <td>
                            {c.call_type === "DATA"
                              ? `${(c.bytes_transferred / (1024 * 1024)).toFixed(1)} MB`
                              : `${c.duration_seconds}s`}
                          </td>
                          <td><strong>${c.rated_amount?.toFixed(2)}</strong></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
