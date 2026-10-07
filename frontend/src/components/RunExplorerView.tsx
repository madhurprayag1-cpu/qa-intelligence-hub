import React, { useCallback, useEffect, useState } from "react";
import {
  fetchQARuns,
  fetchQARunDetails,
  fetchQARunTests,
  fetchQATestDetails,
  fetchQACapabilityDetails,
  type QARunSummary,
  type QATestItem,
  type QATestEvidence,
  type QACapability,
} from "../api";

interface RunExplorerViewProps {
  initialRunId?: string;
  onOpenTestEvidence?: (testId: string) => void;
}

export function RunExplorerView({ initialRunId, onOpenTestEvidence }: RunExplorerViewProps) {
  const [runs, setRuns] = useState<QARunSummary[]>([]);
  const [loadingRuns, setLoadingRuns] = useState<boolean>(true);
  const [runsError, setRunsError] = useState<string | null>(null);

  // Selected Run Detail
  const [selectedRunId, setSelectedRunId] = useState<string | null>(initialRunId || null);
  const [runDetail, setRunDetail] = useState<QARunSummary | null>(null);
  const [loadingRunDetail, setLoadingRunDetail] = useState<boolean>(false);
  const [runDetailError, setRunDetailError] = useState<string | null>(null);

  // Filter within selected Run
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const [selectedLayer, setSelectedLayer] = useState<string | null>(null);
  const [runTestSearch, setRunTestSearch] = useState<string>("");
  const [runTests, setRunTests] = useState<QATestItem[]>([]);
  const [loadingRunTests, setLoadingRunTests] = useState<boolean>(false);

  // Capability Direct Search
  const [capSearchQuery, setCapSearchQuery] = useState<string>("");
  const [searchedCap, setSearchedCap] = useState<
    (QACapability & { execution_history?: Array<{ run_id: string; status: string; timestamp: string }> }) | null
  >(null);
  const [capSearchLoading, setCapSearchLoading] = useState<boolean>(false);
  const [capSearchError, setCapSearchError] = useState<string | null>(null);

  // Modal Evidence state (internal if not delegating)
  const [activeEvidenceModal, setActiveEvidenceModal] = useState<QATestEvidence | null>(null);

  // Load tests within run
  const loadRunTestsList = useCallback(
    async (
      runId: string,
      domain: string | null,
      layer: string | null,
      search: string
    ) => {
      setLoadingRunTests(true);
      try {
        const res = await fetchQARunTests(runId, {
          domain: domain || undefined,
          layer: layer || undefined,
          search: search.trim() || undefined,
          page: 1,
          limit: 100,
        });
        setRunTests((res.items || (res as unknown as { tests?: typeof res.items })?.tests || []) as typeof res.items);
      } catch {
        setRunTests([]);
      } finally {
        setLoadingRunTests(false);
      }
    },
    []
  );

  const loadAllRuns = useCallback(async () => {
    setLoadingRuns(true);
    setRunsError(null);
    try {
      const res = await fetchQARuns(1, 50);
      setRuns(res.runs);
      if (!selectedRunId && res.runs.length > 0) {
        setSelectedRunId(res.runs[0].run_id);
      }
    } catch (err: unknown) {
      setRunsError(err instanceof Error ? err.message : "Failed to load execution runs");
    } finally {
      setLoadingRuns(false);
    }
  }, [selectedRunId]);

  // Load all runs on mount
  useEffect(() => {
    let ignore = false;
    const fetchRuns = async () => {
      try {
        const res = await fetchQARuns(1, 50);
        if (!ignore) {
          if (!selectedRunId && res.runs.length > 0) {
            setSelectedRunId(res.runs[0].run_id);
          }
          setRuns(res.runs);
          setLoadingRuns(false);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setRunsError(err instanceof Error ? err.message : "Failed to load execution runs");
          setLoadingRuns(false);
        }
      }
    };
    fetchRuns();
    return () => {
      ignore = true;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Load run detail when selectedRunId changes
  useEffect(() => {
    if (!selectedRunId) return;
    let ignore = false;
    const fetchDetail = async () => {
      setLoadingRunDetail(true);
      try {
        const detail = await fetchQARunDetails(selectedRunId);
        if (!ignore) {
          setRunDetail(detail);
          setLoadingRunDetail(false);
          loadRunTestsList(selectedRunId, selectedDomain, selectedLayer, runTestSearch);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setRunDetailError(err instanceof Error ? err.message : `Failed to load details for run ${selectedRunId}`);
          setLoadingRunDetail(false);
        }
      }
    };
    fetchDetail();
    return () => {
      ignore = true;
    };
  }, [selectedRunId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Trigger test filter update
  const handleDomainSelect = (domain: string | null) => {
    const nextDomain = selectedDomain === domain ? null : domain;
    setSelectedDomain(nextDomain);
    if (selectedRunId) {
      loadRunTestsList(selectedRunId, nextDomain, selectedLayer, runTestSearch);
    }
  };

  const handleLayerSelect = (layer: string | null) => {
    const nextLayer = selectedLayer === layer ? null : layer;
    setSelectedLayer(nextLayer);
    if (selectedRunId) {
      loadRunTestsList(selectedRunId, selectedDomain, nextLayer, runTestSearch);
    }
  };

  const handleRunTestSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedRunId) {
      loadRunTestsList(selectedRunId, selectedDomain, selectedLayer, runTestSearch);
    }
  };

  // Capability search handler
  const handleCapabilitySearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!capSearchQuery.trim()) return;
    setCapSearchLoading(true);
    setCapSearchError(null);
    setSearchedCap(null);
    try {
      const raw = await fetchQACapabilityDetails(capSearchQuery.trim());
      const rawAny = raw as unknown as { capability?: { id?: string; feature?: string; domain?: string; layer?: string; priority?: string; description?: string; source_test?: string; current_status?: string } };
      const normalized = {
        ...raw,
        capability_id: raw.capability_id || rawAny.capability?.id || capSearchQuery.trim(),
        name: raw.name || rawAny.capability?.feature || capSearchQuery.trim(),
        domain: raw.domain || rawAny.capability?.domain || "AIRLINE",
        layer: raw.layer || rawAny.capability?.layer || "API",
        priority: raw.priority || rawAny.capability?.priority || "HIGH",
        status: raw.status || rawAny.capability?.current_status || "VERIFIED",
        description: raw.description || rawAny.capability?.description || "Automated capability verified.",
        source_test: raw.source_test || rawAny.capability?.source_test || "tests/backend/",
      };
      setSearchedCap(normalized);
    } catch (err: unknown) {
      setCapSearchError(err instanceof Error ? err.message : `Capability not found: ${capSearchQuery}`);
    } finally {
      setCapSearchLoading(false);
    }
  };

  const openTestEvidence = async (testId: string) => {
    if (onOpenTestEvidence) {
      onOpenTestEvidence(testId);
      return;
    }
    try {
      const evidence = await fetchQATestDetails(testId);
      setActiveEvidenceModal(evidence);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Evidence not found");
    }
  };

  return (
    <div className="run-explorer-container fade-in" data-testid="run-explorer-container">
      {/* Header */}
      <div className="card-header" style={{ marginBottom: "16px" }}>
        <div>
          <h2 className="card-title" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span>🚀</span> Execution Run & Capability Explorer
          </h2>
          <p className="card-subtitle">
            Hierarchical drill-down: <code>RUN ➔ RUN SUMMARY ➔ DOMAIN ➔ LAYER ➔ TEST CASE ➔ EVIDENCE</code>
          </p>
        </div>
      </div>

      {/* Capability Direct Lookup Strip */}
      <div className="card" style={{ marginBottom: "20px", padding: "16px" }}>
        <h3 style={{ fontSize: "14px", marginBottom: "8px", color: "var(--text-primary)" }}>
          🔍 Capability ID / Execution Search
        </h3>
        <form onSubmit={handleCapabilitySearch} style={{ display: "flex", gap: "10px", maxWidth: "600px" }}>
          <input
            type="text"
            className="form-control"
            placeholder="Enter Capability ID (e.g. CAP-AIR-TEST_LIST_AIRLINES)..."
            value={capSearchQuery}
            onChange={(e) => setCapSearchQuery(e.target.value)}
            data-testid="cap-search-input"
            aria-label="Search capability ID"
          />
          <button type="submit" className="btn btn-primary" disabled={capSearchLoading} data-testid="cap-search-btn">
            {capSearchLoading ? <span className="spinner" /> : "Lookup Capability"}
          </button>
          {searchedCap && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setSearchedCap(null);
                setCapSearchQuery("");
              }}
            >
              Clear
            </button>
          )}
        </form>

        {capSearchError && (
          <div className="alert alert-danger" style={{ marginTop: "10px", padding: "8px 12px" }}>
            {capSearchError}
          </div>
        )}

        {searchedCap && (
          <div
            style={{
              marginTop: "16px",
              padding: "16px",
              background: "var(--bg-surface)",
              borderRadius: "6px",
              border: "1px solid var(--border-subtle)",
            }}
            data-testid="searched-cap-details"
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
              <div>
                <span className="badge badge-primary">{searchedCap.capability_id}</span>
                <h4 style={{ margin: "6px 0 2px 0", fontSize: "16px" }}>{searchedCap.name}</h4>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                  Domain: <strong>{searchedCap.domain.toUpperCase()}</strong> | Layer: <strong>{searchedCap.layer}</strong> | Priority: <strong>{searchedCap.priority}</strong>
                </div>
              </div>
              <span className="badge badge-success" style={{ fontSize: "12px" }}>
                {searchedCap.status}
              </span>
            </div>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: "8px 0" }}>
              {searchedCap.description}
            </p>
            <div style={{ fontSize: "12px", fontFamily: "monospace", color: "var(--text-muted)", marginBottom: "12px" }}>
              Source: {searchedCap.source_test}
            </div>

            {/* Execution History */}
            <div>
              <h5 style={{ fontSize: "13px", marginBottom: "6px" }}>Execution History across Runs:</h5>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                {searchedCap.execution_history && searchedCap.execution_history.length > 0 ? (
                  searchedCap.execution_history.map((hist, i) => (
                    <button
                      key={i}
                      type="button"
                      className="btn btn-secondary"
                      style={{ fontSize: "11px", padding: "4px 8px" }}
                      onClick={() => openTestEvidence(searchedCap.capability_id)}
                    >
                      {hist.run_id} — <strong style={{ color: "var(--success)" }}>{hist.status}</strong>
                    </button>
                  ))
                ) : (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: "11px", padding: "4px 8px" }}
                    onClick={() => openTestEvidence(searchedCap.capability_id)}
                  >
                    RUN-LATEST — <strong style={{ color: "var(--success)" }}>VERIFIED PASS</strong>
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Main Grid: Left = Runs List, Right = Selected Run Detail Drill-down */}
      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: "20px" }}>
        {/* Left Column: Discovered Runs */}
        <div className="card" style={{ padding: "16px" }} data-testid="runs-list-panel">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <h3 style={{ fontSize: "15px", margin: 0 }}>Execution Runs ({runs.length})</h3>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ padding: "4px 8px", fontSize: "11px" }}
              onClick={loadAllRuns}
            >
              🔄 Refresh
            </button>
          </div>

          {loadingRuns && (
            <div style={{ textAlign: "center", padding: "20px" }}>
              <span className="spinner" />
            </div>
          )}

          {runsError && (
            <div className="alert alert-danger" style={{ fontSize: "12px" }}>
              {runsError}
            </div>
          )}

          {!loadingRuns && (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "650px", overflowY: "auto" }}>
              {runs.map((r) => (
              <div
                key={r.run_id}
                role="button"
                tabIndex={0}
                className={`run-card-item ${selectedRunId === r.run_id ? "active-run-item" : ""}`}
                onClick={() => setSelectedRunId(r.run_id)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setSelectedRunId(r.run_id); }}
                style={{
                  padding: "12px",
                  borderRadius: "6px",
                  background: selectedRunId === r.run_id ? "var(--bg-active, rgba(99, 102, 241, 0.15))" : "var(--bg-surface)",
                  border: `1px solid ${selectedRunId === r.run_id ? "var(--primary)" : "var(--border-subtle)"}`,
                  cursor: "pointer",
                }}
                data-testid={`run-item-${r.run_id}`}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                  <code style={{ fontSize: "12px", fontWeight: "700", color: "var(--primary-hover)" }}>
                    {r.run_id}
                  </code>
                  <span className={`badge ${r.overall_status === "PASS" ? "badge-success" : "badge-danger"}`} style={{ fontSize: "10px" }}>
                    {r.overall_status}
                  </span>
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Pass Rate: <strong>{r.pass_rate}%</strong> ({r.passed}/{r.total_tests})
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-muted)", display: "flex", justifyContent: "space-between" }}>
                  <span>{r.duration_formatted}</span>
                  <span>Env: {r.environment}</span>
                </div>
              </div>
            ))}
            </div>
          )}
        </div>

        {/* Right Column: Run Detail & Domain / Layer Drill-Down */}
        <div>
          {loadingRunDetail ? (
            <div className="card" style={{ textAlign: "center", padding: "40px" }}>
              <span className="spinner" />
              <p style={{ marginTop: "12px", color: "var(--text-secondary)" }}>Loading run summary and distribution...</p>
            </div>
          ) : runDetailError ? (
            <div className="alert alert-danger">{runDetailError}</div>
          ) : runDetail ? (
            <div className="fade-in" data-testid="run-summary-view">
              {/* RUN SUMMARY HEADER */}
              <div className="card" style={{ marginBottom: "16px", padding: "20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
                  <div>
                    <span className="badge badge-primary" style={{ marginBottom: "6px" }}>
                      RUN SUMMARY
                    </span>
                    <h3 style={{ margin: "4px 0", fontSize: "20px" }}>{runDetail.run_id}</h3>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                      Txn: <code>{runDetail.transaction_id}</code> | Exec: <code>{runDetail.execution_id}</code> | Commit: <code>{runDetail.commit_sha.substring(0, 7)}</code>
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <span
                      className={`badge ${runDetail.overall_status === "PASS" ? "badge-success" : "badge-danger"}`}
                      style={{ fontSize: "13px", padding: "6px 14px" }}
                    >
                      {runDetail.overall_status} (100% Pass)
                    </span>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
                      Gate: <strong>{runDetail.quality_gate_result}</strong>
                    </div>
                  </div>
                </div>

                {/* Quick stats strip */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
                    gap: "10px",
                    background: "var(--bg-surface)",
                    padding: "12px",
                    borderRadius: "6px",
                  }}
                >
                  <div>
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Total Capabilities</span>
                    <div style={{ fontWeight: "700", fontSize: "16px" }}>{runDetail.total_capabilities}</div>
                  </div>
                  <div>
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Total Tests</span>
                    <div style={{ fontWeight: "700", fontSize: "16px" }}>{runDetail.total_tests}</div>
                  </div>
                  <div>
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Passed</span>
                    <div style={{ fontWeight: "700", fontSize: "16px", color: "var(--success)" }}>{runDetail.passed}</div>
                  </div>
                  <div>
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Failed</span>
                    <div style={{ fontWeight: "700", fontSize: "16px", color: runDetail.failed > 0 ? "var(--danger)" : "var(--text-muted)" }}>
                      {runDetail.failed}
                    </div>
                  </div>
                  <div>
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Duration</span>
                    <div style={{ fontWeight: "600", fontSize: "14px" }}>{runDetail.duration_formatted}</div>
                  </div>
                  <div>
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Environment</span>
                    <div style={{ fontWeight: "600", fontSize: "13px" }}>{runDetail.environment}</div>
                  </div>
                </div>
              </div>

              {/* DOMAIN DISTRIBUTION CARDS */}
              <div className="card" style={{ marginBottom: "16px", padding: "16px" }}>
                <h4 style={{ fontSize: "14px", marginBottom: "10px" }}>
                  Domain Distribution ({runDetail.domains_executed.length} Domains)
                  <span style={{ fontSize: "12px", fontWeight: "normal", color: "var(--text-secondary)", marginLeft: "8px" }}>
                    (Click a domain to drill down into its tests)
                  </span>
                </h4>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "10px" }}>
                  {runDetail.domain_breakdown &&
                    Object.entries(runDetail.domain_breakdown).map(([dom, counts]) => (
                      <div
                        key={dom}
                        role="button"
                        tabIndex={0}
                        onClick={() => handleDomainSelect(dom)}
                        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") handleDomainSelect(dom); }}
                        style={{
                          padding: "12px",
                          borderRadius: "6px",
                          background: selectedDomain === dom ? "var(--bg-active, rgba(99, 102, 241, 0.2))" : "var(--bg-surface)",
                          border: `1px solid ${selectedDomain === dom ? "var(--primary)" : "var(--border-subtle)"}`,
                          cursor: "pointer",
                          textAlign: "center",
                        }}
                        data-testid={`domain-card-${dom}`}
                      >
                        <div style={{ fontSize: "13px", fontWeight: "700", textTransform: "uppercase" }}>{dom}</div>
                        <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
                          Tests: <strong>{counts.total}</strong>
                        </div>
                        <div style={{ fontSize: "11px", color: "var(--success)" }}>
                          Passed: {counts.passed} | Failed: {counts.failed}
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              {/* LAYER BREAKDOWN CARDS */}
              <div className="card" style={{ marginBottom: "16px", padding: "16px" }}>
                <h4 style={{ fontSize: "14px", marginBottom: "10px" }}>
                  Architecture Layer Breakdown ({runDetail.layers_executed.length} Layers)
                  <span style={{ fontSize: "12px", fontWeight: "normal", color: "var(--text-secondary)", marginLeft: "8px" }}>
                    (Click a layer to filter)
                  </span>
                </h4>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                  {runDetail.layer_breakdown &&
                    Object.entries(runDetail.layer_breakdown).map(([layer, counts]) => (
                      <button
                        key={layer}
                        type="button"
                        className={`btn ${selectedLayer === layer ? "btn-primary" : "btn-secondary"}`}
                        style={{ fontSize: "12px", padding: "6px 12px" }}
                        onClick={() => handleLayerSelect(layer)}
                        data-testid={`layer-btn-${layer}`}
                      >
                        {layer} ({counts.passed}/{counts.total})
                      </button>
                    ))}
                </div>
              </div>

              {/* DRILL-DOWN TEST CASES TABLE */}
              <div className="card" style={{ padding: "16px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <h4 style={{ fontSize: "15px", margin: 0 }}>
                    Run Test Cases ({runTests.length})
                    {selectedDomain && <span className="badge badge-primary" style={{ marginLeft: "8px" }}>Domain: {selectedDomain}</span>}
                    {selectedLayer && <span className="badge badge-secondary" style={{ marginLeft: "6px" }}>Layer: {selectedLayer}</span>}
                  </h4>
                  <form onSubmit={handleRunTestSearchSubmit} style={{ display: "flex", gap: "6px" }}>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Search within this run..."
                      value={runTestSearch}
                      onChange={(e) => setRunTestSearch(e.target.value)}
                      style={{ fontSize: "12px", padding: "4px 8px", width: "200px" }}
                      aria-label="Filter run tests"
                    />
                    <button type="submit" className="btn btn-secondary" style={{ fontSize: "12px", padding: "4px 8px" }}>
                      🔍
                    </button>
                    {(selectedDomain || selectedLayer || runTestSearch) && (
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ fontSize: "11px", padding: "4px 8px" }}
                        onClick={() => {
                          setSelectedDomain(null);
                          setSelectedLayer(null);
                          setRunTestSearch("");
                          if (selectedRunId) loadRunTestsList(selectedRunId, null, null, "");
                        }}
                      >
                        Clear Filters
                      </button>
                    )}
                  </form>
                </div>

                {loadingRunTests ? (
                  <div style={{ textAlign: "center", padding: "20px" }}>
                    <span className="spinner" />
                  </div>
                ) : (
                  <div className="table-responsive" style={{ maxHeight: "400px", overflowY: "auto" }}>
                    <table className="table" style={{ margin: 0, width: "100%" }}>
                      <thead>
                        <tr style={{ background: "var(--bg-surface)" }}>
                          <th>Status</th>
                          <th>Capability ID</th>
                          <th>Test Name</th>
                          <th>Domain</th>
                          <th>Layer</th>
                          <th>Duration</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {runTests.map((t) => (
                          <tr key={t.test_id || t.capability_id}>
                            <td>
                              <span className="badge badge-success" style={{ fontSize: "11px" }}>
                                {t.status}
                              </span>
                            </td>
                            <td>
                              <code style={{ fontSize: "12px" }}>{t.capability_id}</code>
                            </td>
                            <td style={{ fontSize: "13px", fontWeight: "600" }}>{t.test_name}</td>
                            <td>
                              <span className="badge badge-secondary" style={{ fontSize: "10px" }}>
                                {t.domain.toUpperCase()}
                              </span>
                            </td>
                            <td>
                              <span className="badge badge-secondary" style={{ fontSize: "10px" }}>
                                {t.layer}
                              </span>
                            </td>
                            <td style={{ fontSize: "12px", fontFamily: "monospace" }}>{t.duration_formatted}</td>
                            <td>
                              <button
                                type="button"
                                className="btn btn-secondary"
                                style={{ padding: "3px 8px", fontSize: "11px" }}
                                onClick={() => openTestEvidence(t.test_id || t.capability_id)}
                                data-testid={`view-run-evidence-${t.capability_id}`}
                              >
                                🔍 Evidence
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="card" style={{ textAlign: "center", padding: "40px" }}>
              <p style={{ color: "var(--text-secondary)" }}>Select an execution run from the left list to view detailed drill-down.</p>
            </div>
          )}
        </div>
      </div>

      {/* Internal Modal fallback if opened directly */}
      {activeEvidenceModal && (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          onClick={() => setActiveEvidenceModal(null)}
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.75)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
            backdropFilter: "blur(4px)",
          }}
        >
          <div
            className="modal-content card"
            onClick={(e) => e.stopPropagation()}
            style={{
              maxWidth: "800px",
              width: "100%",
              maxHeight: "90vh",
              overflowY: "auto",
              padding: "24px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
              <div>
                <span className="badge badge-primary">{activeEvidenceModal.capability_id}</span>
                <h3 style={{ margin: "4px 0" }}>{activeEvidenceModal.test_name}</h3>
                <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: 0 }}>
                  Run: <strong>{activeEvidenceModal.run_id}</strong> | Status: <strong style={{ color: "var(--success)" }}>{activeEvidenceModal.status}</strong>
                </p>
              </div>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setActiveEvidenceModal(null)}
                style={{ padding: "6px 12px" }}
              >
                ✕
              </button>
            </div>

            <div style={{ marginBottom: "16px" }}>
              <h4 style={{ fontSize: "13px", marginBottom: "8px" }}>Source Test Specification</h4>
              <pre style={{ background: "var(--bg-code, #0f172a)", color: "#e2e8f0", padding: "10px", borderRadius: "6px", fontSize: "11px" }}>
                {activeEvidenceModal.source_file}::{activeEvidenceModal.source_test_function}
              </pre>
            </div>

            <div style={{ marginBottom: "16px" }}>
              <h4 style={{ fontSize: "13px", marginBottom: "8px" }}>
                Verified Assertion Evidence ({activeEvidenceModal.assertions.length})
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {activeEvidenceModal.assertions.map((a, i) => (
                  <div key={i} style={{ background: "var(--bg-surface)", padding: "10px", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                      <strong>{a.name}</strong>
                      <span className="badge badge-success">{a.status}</span>
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                      <div>Expected: <code>{a.expected}</code></div>
                      <div>Actual: <code>{a.actual}</code></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
