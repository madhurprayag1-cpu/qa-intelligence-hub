import React, { useEffect, useState } from "react";
import {
  createFintechAccount,
  evaluateFintechFraud,
  executeFintechTransfer,
  fetchFintechAccounts,
  fetchFintechTransactions,
  submitFintechSwiftTransfer,
  verifyFintechKYC,
} from "../api";
import type {
  BankAccount,
  FraudEvaluationResponse,
  KYCVerificationResponse,
  LedgerTransaction,
} from "../types";

export function FinTechView() {
  // State: Accounts & Active Selection
  const [accounts, setAccounts] = useState<BankAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [transactions, setTransactions] = useState<LedgerTransaction[]>([]);

  // State: Account Creation
  const [newHolder, setNewHolder] = useState("Alex Vance");
  const [newEmail, setNewEmail] = useState("alex.vance@example.org");
  const [newCurrency, setNewCurrency] = useState("USD");
  const [newType, setNewType] = useState("CHECKING");
  const [newInitialBalance, setNewInitialBalance] = useState("5000");

  // State: KYC Onboarding
  const [kycCustomerId, setKycCustomerId] = useState("CUST-FT-101");
  const [kycFullName, setKycFullName] = useState("Alex Vance");
  const [kycIncome, setKycIncome] = useState("7500");
  const [kycDob, setKycDob] = useState("1988-11-20");
  const [kycDocNum, setKycDocNum] = useState("PASSPORT-US-998822");
  const [kycResult, setKycResult] = useState<KYCVerificationResponse | null>(null);

  // State: Fund Transfer
  const [transferSource, setTransferSource] = useState<string>("");
  const [transferDest, setTransferDest] = useState<string>("");
  const [transferAmount, setTransferAmount] = useState<string>("250.00");
  const [transferDefect, setTransferDefect] = useState<string>("");
  const [lastTransferResult, setLastTransferResult] = useState<LedgerTransaction | null>(null);

  // State: SWIFT / ISO 20022
  const [swiftMsgId, setSwiftMsgId] = useState("MSG-2026-PAIN001-01");
  const [debtorIban, setDebtorIban] = useState("US89370400440532013000");
  const [creditorIban, setCreditorIban] = useState("GB29NWBK60161331926819");
  const [swiftAmount, setSwiftAmount] = useState("15000.00");
  const [swiftCurrency, setSwiftCurrency] = useState("USD");
  const [swiftResult, setSwiftResult] = useState<Record<string, unknown> | null>(null);

  // State: Fraud Engine
  const [fraudAccountId, setFraudAccountId] = useState("ACC-FT-001");
  const [fraudAmount, setFraudAmount] = useState("12000.00");
  const [fraudVelocity, setFraudVelocity] = useState("5");
  const [fraudOrigin, setFraudOrigin] = useState("US");
  const [fraudDest, setFraudDest] = useState("NG");
  const [fraudDefect, setFraudDefect] = useState<string>("");
  const [fraudResult, setFraudResult] = useState<FraudEvaluationResponse | null>(null);

  // Status & Feedback
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadTransactions = async (accId: string) => {
    try {
      const txns = await fetchFintechTransactions(accId);
      setTransactions(txns);
    } catch {
      setTransactions([]);
    }
  };

  const loadAccounts = async () => {
    try {
      let accs = await fetchFintechAccounts().catch(() => []);
      if (accs.length === 0) {
        // Seed default accounts if store is brand new
        const seed1: BankAccount = {
          account_id: "ACC-FT-001",
          account_holder: "Alex Vance",
          email: "alex.vance@example.org",
          iban: "US89370400440532013000",
          bic_swift: "CHASUS33XXX",
          currency: "USD",
          balance: 10000.0,
          account_type: "CHECKING",
          kyc_tier: "TIER_2_VERIFIED",
          is_active: true,
        };
        const seed2: BankAccount = {
          account_id: "ACC-FT-002",
          account_holder: "Morgan Stanley Corp",
          email: "treasury@morgan.example",
          iban: "US99370400440532019999",
          bic_swift: "CITIUS33XXX",
          currency: "USD",
          balance: 25000.0,
          account_type: "ESCROW",
          kyc_tier: "TIER_3_ENHANCED",
          is_active: true,
        };
        await createFintechAccount(seed1).catch(() => {});
        await createFintechAccount(seed2).catch(() => {});
        accs = [seed1, seed2];
      }
      setAccounts(accs);
      if (accs.length > 0) {
        const first = accs[0].account_id;
        setSelectedAccountId(first);
        setTransferSource(first);
        if (accs.length > 1) {
          setTransferDest(accs[1].account_id);
        }
        await loadTransactions(first);
      }
    } catch {
      // Hermetic fallback
    }
  };

  useEffect(() => {
    let isMounted = true;
    (async () => {
      await Promise.resolve();
      if (isMounted) {
        await loadAccounts();
      }
    })();
    return () => {
      isMounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 1. KYC Verification
  const handleVerifyKYC = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const res = await verifyFintechKYC({
        customer_id: kycCustomerId,
        full_name: kycFullName,
        date_of_birth: kycDob,
        tax_id_masked: kycDocNum,
        monthly_income: parseFloat(kycIncome) || 0.0,
      });
      setKycResult(res);
      setSuccessMsg(
        `KYC Verification Result: ${res.status} (Assigned Tier: ${res.assigned_tier}, Daily Limit: $${res.daily_transfer_limit.toLocaleString()}).`
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "KYC verification failed");
    } finally {
      setLoading(false);
    }
  };

  // 2. Open Account
  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const accId = `ACC-FT-${Math.floor(100 + Math.random() * 900)}`;
      const randomIban = `US${Math.floor(100000000000000000 + Math.random() * 900000000000000000)}`;
      const newAcc: BankAccount = {
        account_id: accId,
        account_holder: newHolder,
        email: newEmail,
        iban: randomIban,
        bic_swift: "CHASUS33XXX",
        currency: newCurrency,
        balance: parseFloat(newInitialBalance) || 0.0,
        account_type: newType,
        kyc_tier: kycResult?.assigned_tier || "TIER_1_BASIC",
        is_active: true,
      };

      const res = await createFintechAccount(newAcc);
      const updated = await fetchFintechAccounts().catch(() => [...accounts, res]);
      setAccounts(updated);
      setSelectedAccountId(res.account_id);
      setSuccessMsg(`Bank Account ${res.account_id} created with initial balance $${res.balance.toFixed(2)}.`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Account creation failed");
    } finally {
      setLoading(false);
    }
  };

  // 3. Execute Transfer
  const handleExecuteTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const amt = parseFloat(transferAmount);
      if (isNaN(amt) || amt <= 0) {
        throw new Error("Enter a valid positive transfer amount");
      }
      if (transferSource === transferDest) {
        throw new Error("Source and destination accounts must be distinct");
      }

      const res = await executeFintechTransfer(
        {
          source_account_id: transferSource,
          destination_account_id: transferDest,
          amount: amt,
        },
        transferDefect ? transferDefect : undefined
      );

      setLastTransferResult(res);
      setSuccessMsg(
        `Transfer ${res.transaction_id} SETTLED: $${amt.toFixed(2)} transferred from ${transferSource} to ${transferDest}.`
      );

      // Refresh accounts & ledger
      await loadAccounts();
      if (selectedAccountId) {
        await loadTransactions(selectedAccountId);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Transfer execution failed");
    } finally {
      setLoading(false);
    }
  };

  // 4. Submit SWIFT pain.001 Transfer
  const handleSwiftTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const amt = parseFloat(swiftAmount);
      if (isNaN(amt) || amt <= 0) throw new Error("Enter valid SWIFT amount");

      const res = await submitFintechSwiftTransfer({
        message_id: swiftMsgId,
        instruction_id: `INST-${Date.now()}`,
        debtor_iban: debtorIban,
        creditor_iban: creditorIban,
        instructed_amount: amt,
        instructed_currency: swiftCurrency,
      });

      setSwiftResult(res);
      setSuccessMsg(
        `SWIFT ISO 20022 message processed: Status ${res.status}, Amount ${swiftCurrency} ${amt}.`
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "SWIFT processing failed");
    } finally {
      setLoading(false);
    }
  };

  // 5. Evaluate Fraud Risk
  const handleEvaluateFraud = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const amt = parseFloat(fraudAmount);
      const vel = parseInt(fraudVelocity, 10);

      const res = await evaluateFintechFraud(
        {
          account_id: fraudAccountId,
          amount: amt,
          transactions_in_last_minute: vel,
          origin_country: fraudOrigin,
          destination_country: fraudDest,
        },
        fraudDefect ? fraudDefect : undefined
      );

      setFraudResult(res);
      setSuccessMsg(
        `Fraud Evaluation: Risk Score ${res.risk_score}/100 • Verdict: ${res.action}.`
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Fraud evaluation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="domain-view fintech-view" data-testid="fintech-view">
      {/* Banner */}
      <section className="domain-banner" data-testid="fintech-banner">
        <div className="domain-banner-header">
          <div className="domain-badge-group">
            <span className="domain-pill" style={{ background: "rgba(59, 130, 246, 0.2)", color: "#60a5fa", border: "1px solid rgba(59, 130, 246, 0.4)" }}>
              💳 FINTECH & DIGITAL BANKING SUT
            </span>
            <span className="domain-standard-tag">Double-Entry Ledger • ISO 20022 SWIFT • KYC/AML • Fraud 2FA</span>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={loadAccounts}
            data-testid="fintech-refresh-btn"
          >
            🔄 Refresh Accounts
          </button>
        </div>
        <p className="domain-desc">
          Execute realistic FinTech workflows: Customer KYC verification & AML screening, multi-currency bank account management,
          atomic double-entry fund transfers, ISO 20022 pain.001 SWIFT initiation, and real-time fraud risk evaluation.
        </p>
      </section>

      {/* Global Alerts */}
      {error && (
        <div className="alert alert-danger fade-in" role="alert" data-testid="fintech-error-banner">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {successMsg && !error && (
        <div className="alert alert-success fade-in" role="alert" data-testid="fintech-success-banner">
          <span>✅</span>
          <span>{successMsg}</span>
        </div>
      )}

      <div className="domain-grid">
        {/* LEFT COLUMN: KYC Onboarding & Double-Entry Transfers */}
        <div className="domain-card-column">
          {/* KYC Onboarding Card */}
          <section className="form-card" data-testid="kyc-onboarding-card">
            <div className="card-header-styled">
              <span className="step-num">1</span>
              <div>
                <h3>Customer KYC & AML Identity Verification</h3>
                <p className="subtext">Verify identity, evaluate sanctions lists, and assign daily transfer limit tier</p>
              </div>
            </div>

            <form onSubmit={handleVerifyKYC} data-testid="kyc-form">
              <div className="form-group mb-2">
                <label htmlFor="ft-kyc-custid">Customer Identifier</label>
                <input
                  id="ft-kyc-custid"
                  type="text"
                  value={kycCustomerId}
                  onChange={(e) => setKycCustomerId(e.target.value)}
                  required
                  data-testid="input-kyc-customer-id"
                />
              </div>
              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="ft-kyc-name">Full Customer Name</label>
                  <input
                    id="ft-kyc-name"
                    type="text"
                    value={kycFullName}
                    onChange={(e) => setKycFullName(e.target.value)}
                    required
                    data-testid="input-kyc-name"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="ft-kyc-income">Verified Monthly Income ($)</label>
                  <input
                    id="ft-kyc-income"
                    type="number"
                    step="100"
                    value={kycIncome}
                    onChange={(e) => setKycIncome(e.target.value)}
                    required
                    data-testid="input-kyc-income"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="ft-kyc-dob">Date of Birth</label>
                  <input
                    id="ft-kyc-dob"
                    type="date"
                    value={kycDob}
                    onChange={(e) => setKycDob(e.target.value)}
                    required
                    data-testid="input-kyc-dob"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="ft-kyc-doc">Identity Document #</label>
                  <input
                    id="ft-kyc-doc"
                    type="text"
                    value={kycDocNum}
                    onChange={(e) => setKycDocNum(e.target.value)}
                    required
                    data-testid="input-kyc-doc"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-block"
                disabled={loading}
                data-testid="submit-kyc-btn"
              >
                {loading ? "Verifying..." : "🛡️ Run KYC & OFAC Sanctions Verification"}
              </button>
            </form>

            {/* KYC Result Pill Box */}
            {kycResult && (
              <div className="status-box mt-4" data-testid="kyc-result-box">
                <div className="status-box-header">
                  <span
                    className={`status-pill ${kycResult.status === "APPROVED" ? "status-pill-online" : "status-pill-offline"}`}
                    data-testid="kyc-status-badge"
                  >
                    STATUS: {kycResult.status}
                  </span>
                  <span className="status-pill status-pill-online" data-testid="kyc-tier-badge">
                    {kycResult.assigned_tier}
                  </span>
                </div>
                <div className="patient-meta-grid mt-2">
                  <div>
                    <span className="meta-label">Daily Transfer Limit:</span>
                    <strong data-testid="kyc-daily-limit" style={{ color: "#38bdf8" }}>
                      ${kycResult.daily_transfer_limit.toLocaleString()} / day
                    </strong>
                  </div>
                  <div>
                    <span className="meta-label">OFAC Sanctions:</span>
                    <strong
                      data-testid="kyc-sanctions-badge"
                      style={{ color: kycResult.pep_sanctions_cleared ? "#10b981" : "#f43f5e" }}
                    >
                      {kycResult.pep_sanctions_cleared ? "CLEARED" : "WATCHLIST MATCH"}
                    </strong>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* Double-Entry Fund Transfer */}
          <section className="form-card mt-4" data-testid="fund-transfer-card">
            <div className="card-header-styled">
              <span className="step-num">2</span>
              <div>
                <h3>Atomic Double-Entry Ledger Transfer</h3>
                <p className="subtext">Execute atomic credit/debit with strict balance & KYC limit verification</p>
              </div>
            </div>

            <form onSubmit={handleExecuteTransfer} data-testid="transfer-form">
              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="ft-source-acc">Source Account (Debit)</label>
                  <select
                    id="ft-source-acc"
                    value={transferSource}
                    onChange={(e) => setTransferSource(e.target.value)}
                    data-testid="select-transfer-source"
                  >
                    {accounts.map((a) => (
                      <option key={a.account_id} value={a.account_id}>
                        {a.account_id} ({a.account_holder} • ${a.balance.toFixed(2)})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="ft-dest-acc">Destination Account (Credit)</label>
                  <select
                    id="ft-dest-acc"
                    value={transferDest}
                    onChange={(e) => setTransferDest(e.target.value)}
                    data-testid="select-transfer-dest"
                  >
                    {accounts.map((a) => (
                      <option key={a.account_id} value={a.account_id}>
                        {a.account_id} ({a.account_holder} • ${a.balance.toFixed(2)})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="ft-transfer-amount">Transfer Amount ($)</label>
                <input
                  id="ft-transfer-amount"
                  type="number"
                  step="0.01"
                  value={transferAmount}
                  onChange={(e) => setTransferAmount(e.target.value)}
                  required
                  data-testid="input-transfer-amount"
                />
              </div>

              {/* Defect injection hook */}
              <div className="defect-hook-box">
                <label htmlFor="ft-transfer-defect" className="defect-label">
                  🧪 QA Ledger Defect Hook:
                </label>
                <select
                  id="ft-transfer-defect"
                  value={transferDefect}
                  onChange={(e) => setTransferDefect(e.target.value)}
                  data-testid="select-transfer-defect"
                >
                  <option value="">None (Enforce Atomic Double-Entry)</option>
                  <option value="DEF-FT-001">
                    DEF-FT-001: Race Condition Double Debit (Balance goes negative)
                  </option>
                  <option value="DOUBLE_DEBIT_RACE">
                    DOUBLE_DEBIT_RACE (DEF-FT-001)
                  </option>
                  <option value="DEF-FT-002">
                    DEF-FT-002: KYC Tier Limit Bypass (Exceeds daily allowance)
                  </option>
                  <option value="KYC_TIER_LIMIT_BYPASS">
                    KYC_TIER_LIMIT_BYPASS (DEF-FT-002)
                  </option>
                </select>
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-block"
                disabled={loading || accounts.length < 2}
                data-testid="submit-transfer-btn"
              >
                {loading ? "Settling..." : "💸 Execute Double-Entry Transfer"}
              </button>
            </form>

            {/* Transfer Result Banner */}
            {lastTransferResult && (
              <div className="status-box mt-4" data-testid="transfer-result-box">
                <div className="status-box-header">
                  <span className="status-pill status-pill-online" data-testid="transfer-txn-id">
                    TXN: {lastTransferResult.transaction_id}
                  </span>
                  <span className="status-pill status-pill-online">
                    STATUS: {lastTransferResult.status}
                  </span>
                </div>
                <div className="patient-meta-grid mt-2">
                  <div>
                    <span className="meta-label">Amount:</span>
                    <strong style={{ color: "#38bdf8" }}>
                      ${lastTransferResult.amount.toFixed(2)} {lastTransferResult.currency}
                    </strong>
                  </div>
                  <div>
                    <span className="meta-label">Source New Balance:</span>
                    <strong>${lastTransferResult.source_new_balance?.toFixed(2)}</strong>
                  </div>
                  <div>
                    <span className="meta-label">Dest New Balance:</span>
                    <strong style={{ color: "#10b981" }}>${lastTransferResult.dest_new_balance?.toFixed(2)}</strong>
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>

        {/* RIGHT COLUMN: Account Overview, ISO 20022, and Fraud Engine */}
        <div className="domain-card-column">
          {/* Account Overview Cards */}
          <section className="form-card" data-testid="accounts-overview-card">
            <div className="card-header-styled">
              <span className="step-num">3</span>
              <div>
                <h3>Bank Account Overview & Balances</h3>
                <p className="subtext">Multi-currency demand deposit accounts and statement inspection</p>
              </div>
            </div>

            <div className="account-cards-grid mt-2" data-testid="accounts-list">
              {accounts.map((acc) => (
                <div
                  key={acc.account_id}
                  className={`account-summary-card ${selectedAccountId === acc.account_id ? "selected-account" : ""}`}
                  onClick={() => {
                    setSelectedAccountId(acc.account_id);
                    loadTransactions(acc.account_id);
                  }}
                  data-testid={`account-card-${acc.account_id}`}
                >
                  <div className="account-header">
                    <strong data-testid="account-id">{acc.account_id}</strong>
                    <span className="status-badge badge-active">{acc.account_type}</span>
                  </div>
                  <div className="account-holder-name">{acc.account_holder}</div>
                  <div className="account-iban" data-testid="account-iban">
                    IBAN: <code>{acc.iban}</code>
                  </div>
                  <div className="account-balance-line">
                    <span className="account-balance" data-testid="account-balance">
                      ${acc.balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {acc.currency}
                    </span>
                    <span className="status-pill status-pill-online">{acc.kyc_tier}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Account Statement & Transaction History */}
            {selectedAccountId && (
              <div className="mt-3" data-testid="account-transactions-wrapper">
                <h4>Statement History for {selectedAccountId} ({transactions.length})</h4>
                {transactions.length === 0 ? (
                  <p className="text-secondary text-sm mt-1">No transaction records found for this account.</p>
                ) : (
                  <div className="table-responsive mt-2">
                    <table className="data-table" data-testid="transactions-table">
                      <thead>
                        <tr>
                          <th>Txn ID</th>
                          <th>Counterparty</th>
                          <th>Amount</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {transactions.map((tx) => (
                          <tr key={tx.transaction_id}>
                            <td><code>{tx.transaction_id}</code></td>
                            <td>{tx.source_account_id === selectedAccountId ? `To ${tx.destination_account_id}` : `From ${tx.source_account_id}`}</td>
                            <td style={{ color: tx.source_account_id === selectedAccountId ? "#f87171" : "#34d399", fontWeight: 700 }}>
                              {tx.source_account_id === selectedAccountId ? "-" : "+"}${tx.amount.toFixed(2)} {tx.currency}
                            </td>
                            <td><span className="status-badge badge-active">{tx.status}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* Quick Create Account Form */}
            <form onSubmit={handleCreateAccount} className="mt-4" data-testid="quick-create-account-form">
              <h4>Open New Synthetic Account</h4>
              <div className="form-row mt-2">
                <div className="form-group flex-1">
                  <label htmlFor="ft-acc-holder">Account Holder</label>
                  <input
                    id="ft-acc-holder"
                    type="text"
                    value={newHolder}
                    onChange={(e) => setNewHolder(e.target.value)}
                    required
                    data-testid="input-new-holder"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="ft-acc-email">Holder Email</label>
                  <input
                    id="ft-acc-email"
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    required
                    data-testid="input-new-email"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="ft-acc-currency">Currency</label>
                  <select
                    id="ft-acc-currency"
                    value={newCurrency}
                    onChange={(e) => setNewCurrency(e.target.value)}
                    data-testid="select-new-currency"
                  >
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="GBP">GBP</option>
                  </select>
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="ft-acc-type">Account Type</label>
                  <select
                    id="ft-acc-type"
                    value={newType}
                    onChange={(e) => setNewType(e.target.value)}
                    data-testid="select-new-type"
                  >
                    <option value="CHECKING">CHECKING</option>
                    <option value="SAVINGS">SAVINGS</option>
                    <option value="ESCROW">ESCROW</option>
                  </select>
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="ft-acc-balance">Initial Balance ($)</label>
                  <input
                    id="ft-acc-balance"
                    type="number"
                    step="50"
                    value={newInitialBalance}
                    onChange={(e) => setNewInitialBalance(e.target.value)}
                    required
                    data-testid="input-new-balance"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-secondary btn-block mt-2"
                disabled={loading}
                data-testid="submit-new-account-btn"
              >
                + Provision New Account
              </button>
            </form>
          </section>

          {/* SWIFT / ISO 20022 pain.001 Initiation */}
          <section className="form-card mt-4" data-testid="swift-iso20022-card">
            <div className="card-header-styled">
              <span className="step-num">4</span>
              <div>
                <h3>ISO 20022 / SWIFT Credit Transfer (pain.001)</h3>
                <p className="subtext">Cross-border interbank financial messaging initiation</p>
              </div>
            </div>

            <form onSubmit={handleSwiftTransfer} data-testid="swift-form">
              <div className="form-group">
                <label htmlFor="ft-swift-msg">Message ID</label>
                <input
                  id="ft-swift-msg"
                  type="text"
                  value={swiftMsgId}
                  onChange={(e) => setSwiftMsgId(e.target.value)}
                  required
                  data-testid="input-swift-msg"
                />
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="ft-debtor-iban">Debtor IBAN (min 15 chars)</label>
                  <input
                    id="ft-debtor-iban"
                    type="text"
                    value={debtorIban}
                    onChange={(e) => setDebtorIban(e.target.value)}
                    required
                    data-testid="input-debtor-iban"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="ft-creditor-iban">Creditor IBAN (min 15 chars)</label>
                  <input
                    id="ft-creditor-iban"
                    type="text"
                    value={creditorIban}
                    onChange={(e) => setCreditorIban(e.target.value)}
                    required
                    data-testid="input-creditor-iban"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="ft-swift-amount">Instructed Amount</label>
                  <input
                    id="ft-swift-amount"
                    type="number"
                    step="100"
                    value={swiftAmount}
                    onChange={(e) => setSwiftAmount(e.target.value)}
                    required
                    data-testid="input-swift-amount"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="ft-swift-currency">Currency</label>
                  <select
                    id="ft-swift-currency"
                    value={swiftCurrency}
                    onChange={(e) => setSwiftCurrency(e.target.value)}
                    data-testid="select-swift-currency"
                  >
                    <option value="USD">USD - US Dollar</option>
                    <option value="EUR">EUR - Euro</option>
                    <option value="GBP">GBP - British Pound</option>
                  </select>
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-secondary btn-block"
                disabled={loading}
                data-testid="submit-swift-btn"
              >
                {loading ? "Transmitting..." : "🌐 Submit pain.001.001.09 Message"}
              </button>
            </form>

            {swiftResult && (
              <div className="status-box mt-4" data-testid="swift-result-box">
                <div className="status-box-header">
                  <span className="status-pill status-pill-online" data-testid="swift-status">
                    {String(swiftResult.status)}
                  </span>
                  <span className="status-pill status-pill-online">
                    {String(swiftResult.iso_standard)}
                  </span>
                </div>
                <div className="mt-2 text-sm text-secondary">
                  Instruction ID: <code data-testid="swift-instruction-id">{String(swiftResult.instruction_id)}</code>
                </div>
              </div>
            )}
          </section>

          {/* Real-time Fraud & 2FA Engine */}
          <section className="form-card mt-4" data-testid="fraud-engine-card">
            <div className="card-header-styled">
              <span className="step-num">5</span>
              <div>
                <h3>Real-Time Fraud & 2FA Risk Assessment</h3>
                <p className="subtext">Continuous transaction monitoring, velocity checks, and impossible travel detection</p>
              </div>
            </div>

            <form onSubmit={handleEvaluateFraud} data-testid="fraud-form">
              <div className="form-group mb-2">
                <label htmlFor="ft-fraud-account">Monitored Account</label>
                <select
                  id="ft-fraud-account"
                  value={fraudAccountId}
                  onChange={(e) => setFraudAccountId(e.target.value)}
                  data-testid="select-fraud-account"
                >
                  {accounts.map((a) => (
                    <option key={a.account_id} value={a.account_id}>
                      {a.account_id} ({a.account_holder})
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="ft-fraud-amount">Transaction Amount ($)</label>
                  <input
                    id="ft-fraud-amount"
                    type="number"
                    value={fraudAmount}
                    onChange={(e) => setFraudAmount(e.target.value)}
                    required
                    data-testid="input-fraud-amount"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="ft-fraud-velocity">Txns In Last Minute</label>
                  <input
                    id="ft-fraud-velocity"
                    type="number"
                    value={fraudVelocity}
                    onChange={(e) => setFraudVelocity(e.target.value)}
                    required
                    data-testid="input-fraud-velocity"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label htmlFor="ft-fraud-origin">Origin Country Code</label>
                  <input
                    id="ft-fraud-origin"
                    type="text"
                    value={fraudOrigin}
                    onChange={(e) => setFraudOrigin(e.target.value)}
                    required
                    data-testid="input-fraud-origin"
                  />
                </div>
                <div className="form-group flex-1">
                  <label htmlFor="ft-fraud-dest">Destination Country Code</label>
                  <input
                    id="ft-fraud-dest"
                    type="text"
                    value={fraudDest}
                    onChange={(e) => setFraudDest(e.target.value)}
                    required
                    data-testid="input-fraud-dest"
                  />
                </div>
              </div>

              {/* Defect injection hook */}
              <div className="defect-hook-box">
                <label htmlFor="ft-fraud-defect" className="defect-label">
                  🧪 QA Fraud Defect Hook:
                </label>
                <select
                  id="ft-fraud-defect"
                  value={fraudDefect}
                  onChange={(e) => setFraudDefect(e.target.value)}
                  data-testid="select-fraud-defect"
                >
                  <option value="">None (Enforce Real-Time Risk Rules)</option>
                  <option value="DEF-FT-004">
                    DEF-FT-004: Fraud Velocity Rule Evasion
                  </option>
                  <option value="DEF-FT-005">
                    DEF-FT-005: Fraud Velocity Limit Bypass (Allows high burst attacks)
                  </option>
                  <option value="FRAUD_VELOCITY_BYPASS">
                    FRAUD_VELOCITY_BYPASS (DEF-FT-004)
                  </option>
                </select>
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-block"
                disabled={loading}
                data-testid="submit-fraud-btn"
              >
                {loading ? "Evaluating..." : "🚨 Evaluate Transaction Risk"}
              </button>
            </form>

            {fraudResult && (
              <div className="status-box mt-4" data-testid="fraud-result-box">
                <div className="status-box-header">
                  <span className="status-pill status-pill-online">
                    Risk Score: <strong data-testid="fraud-risk-score">{fraudResult.risk_score}</strong>/100
                  </span>
                  <span
                    className={`status-pill ${
                      fraudResult.action === "ALLOW"
                        ? "status-pill-online"
                        : fraudResult.action === "CHALLENGE_2FA"
                        ? "status-pill-pending"
                        : "status-pill-offline"
                    }`}
                    data-testid="fraud-action-verdict"
                  >
                    VERDICT: {fraudResult.action}
                  </span>
                </div>
                {fraudResult.detected_anomalies.length > 0 && (
                  <div className="mt-2">
                    <span className="meta-label">Detected Anomalies:</span>
                    <ul className="text-sm mt-1" style={{ paddingLeft: "18px", color: "#fbbf24" }}>
                      {fraudResult.detected_anomalies.map((anom) => (
                        <li key={anom}>{anom}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
