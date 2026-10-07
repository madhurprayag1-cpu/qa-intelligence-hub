import type {
  Airport,
  AncillaryCatalog,
  AncillarySelection,
  Booking,
  Flight,
  FlightListItem,
  HealthStatus,
  PaymentMethod,
  PaymentResponse,
  ThreeDSStatus,
  HealthcarePatient,
  HealthcarePractitioner,
  HealthcareObservation,
  HealthcareAppointment,
  PediatricDosageRequest,
  PediatricDosageResponse,
  BankAccount,
  LedgerTransaction,
  KYCVerificationRequest,
  KYCVerificationResponse,
  FraudEvaluationRequest,
  FraudEvaluationResponse,
  ISO20022CreditTransfer,
  EcommerceProduct,
  CartItem,
  CartValidationResult,
  EcommerceOrder,
  RefundDisbursement,
  TelecomPlan,
  TelecomSubscriber,
  CallDetailRecord,
  RateCDRResponse,
  DefectSummary,
} from "./types";

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL !== undefined
    ? import.meta.env.VITE_API_BASE_URL.trim().replace(/\/$/, "")
    : (import.meta.env.PROD ? "" : "http://127.0.0.1:8000");

let accessToken: string | null = null;

export type DemoUser = { id: number; email: string; name: string; role: string };

export async function login(email: string, password: string): Promise<DemoUser> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail ?? "Login failed");
  accessToken = data.access_token;
  return data.user as DemoUser;
}

export function logout(): void {
  accessToken = null;
}

function authenticatedHeaders(headers: HeadersInit = {}): Headers {
  const result = new Headers(headers);
  if (accessToken) result.set("Authorization", `Bearer ${accessToken}`);
  return result;
}

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function fetchAirports(): Promise<Airport[]> {
  const res = await fetch(`${API_BASE}/airports`);
  if (!res.ok) throw new Error("Failed to load airports");
  return res.json();
}

export async function fetchFlights(): Promise<FlightListItem[]> {
  const res = await fetch(`${API_BASE}/flights`);
  if (!res.ok) throw new Error("Failed to load flights");
  return res.json();
}

export async function searchFlights(
  origin: string,
  destination: string,
  travelDate?: string
): Promise<Flight[]> {
  let url = `${API_BASE}/search/flights?origin=${encodeURIComponent(
    origin
  )}&destination=${encodeURIComponent(destination)}`;
  if (travelDate) {
    url += `&travel_date=${encodeURIComponent(travelDate)}`;
  }
  const response = await fetch(url);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "Flight search failed");
  }
  return response.json();
}

export async function fetchAncillariesCatalog(): Promise<AncillaryCatalog> {
  const response = await fetch(`${API_BASE}/bookings/ancillaries/catalog`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "Failed to fetch ancillary catalog");
  }
  return response.json();
}

export async function createBooking(payload: {
  flight_id: number;
  passenger_name: string;
  passenger_email: string;
  seats: number;
  payment_method?: string;
  ancillaries?: AncillarySelection;
}): Promise<Booking> {
  const res = await fetch(`${API_BASE}/bookings`, {
    method: "POST",
    headers: authenticatedHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "Booking creation failed");
  }
  return res.json();
}

export async function getBookingById(bookingId: number): Promise<Booking> {
  const res = await fetch(`${API_BASE}/bookings/${bookingId}`, { headers: authenticatedHeaders() });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "Booking not found");
  }
  return res.json();
}

export async function getBookingByReference(reference: string): Promise<Booking> {
  const res = await fetch(
    `${API_BASE}/bookings/reference/${encodeURIComponent(reference)}`,
    { headers: authenticatedHeaders() }
  );
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "Booking reference not found");
  }
  return res.json();
}

export async function cancelBooking(bookingId: number): Promise<{
  booking_id: number;
  reference: string;
  previous_status: string;
  current_status: string;
  seats_released: number;
  refund_status: string;
  refund_amount: number;
}> {
  const res = await fetch(`${API_BASE}/bookings/${bookingId}/cancel`, {
    method: "POST",
    headers: authenticatedHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "Booking cancellation failed");
  }
  return res.json();
}

export async function processPayment(payload: {
  booking_id: number;
  method: PaymentMethod;
  three_ds_result?: ThreeDSStatus;
}): Promise<PaymentResponse> {
  const res = await fetch(`${API_BASE}/payments`, {
    method: "POST",
    headers: authenticatedHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "Payment processing failed");
  }
  return res.json();
}

export async function getPayment(bookingId: number): Promise<PaymentResponse> {
  const res = await fetch(`${API_BASE}/payments/${bookingId}`, { headers: authenticatedHeaders() });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "Payment record not found");
  }
  return res.json();
}

export async function fetchDefects(): Promise<import("./types").DefectSummary[]> {
  const res = await fetch(`${API_BASE}/defects`);
  if (!res.ok) throw new Error("Failed to load defect catalog");
  return res.json();
}

export async function fetchAIProviders(): Promise<import("./types").AIProviderInfo> {
  const res = await fetch(`${API_BASE}/ai/providers`);
  if (!res.ok) throw new Error("Failed to fetch AI provider status");
  return res.json();
}

export async function queryRAG(
  query: string,
  documents?: string[]
): Promise<import("./types").RAGQueryResponse> {
  const res = await fetch(`${API_BASE}/ai/rag/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: query, query, documents }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "RAG query failed");
  }
  return res.json();
}

export async function runRCA(
  logs: string,
  component: string = "payments"
): Promise<import("./types").RCAResponse> {
  const res = await fetch(`${API_BASE}/ai/rca`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ error_message: logs, logs, component }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "RCA analysis failed");
  }
  return res.json();
}

export async function evaluateQualityGate(
  payload: Record<string, unknown>
): Promise<import("./types").QualityGateResponse> {
  const res = await fetch(`${API_BASE}/quality-gate/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "Quality gate evaluation failed");
  }
  return res.json();
}

export async function fetchQualityGateRuns(
  limit: number = 10
): Promise<import("./types").QualityGateResponse[]> {
  const res = await fetch(`${API_BASE}/quality-gate/runs?limit=${limit}`);
  if (!res.ok) {
    return [];
  }
  return res.json();
}

export async function auditSecurityPayload(payload: {
  endpoint: string;
  payload: Record<string, unknown>;
  role?: string;
}): Promise<{
  run_id: string;
  status: string;
  report: {
    status: string;
    findings_count: number;
    findings: Array<{
      category: string;
      severity: string;
      description: string;
      location: string;
      remediation: string;
    }>;
    endpoint: string;
    pci_dss_compliant: boolean;
    sanitization_status: string;
  };
}> {
  const res = await fetch(`${API_BASE}/ai/security/audit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "Security audit failed");
  }
  return res.json();
}

export async function fetchQALayers(): Promise<{
  total_layers: number;
  total_tests: number;
  layers: Array<{
    id: string;
    name: string;
    path: string;
    test_count: number;
    description: string;
    layer_type: string;
  }>;
}> {
  const res = await fetch(`${API_BASE}/qa/layers`);
  if (!res.ok) throw new Error("Failed to load QA layers");
  return res.json();
}

export async function calculateRegressionImpact(payload: {
  changed_files?: string[];
  preset?: string;
}): Promise<{
  changed_files: string[];
  selected_test_files: string[];
  selected_tags: string[];
  pytest_command: string;
  playwright_command: string | null;
  reasoning: string[];
  test_count: number;
}> {
  const res = await fetch(`${API_BASE}/qa/regression/impact`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "Regression impact calculation failed");
  }
  return res.json();
}

export async function executeTestRunner(payload: {
  layer?: string;
  tag?: string;
  files?: string[];
  policy_name?: string;
  evaluate_quality_gate?: boolean;
}): Promise<{
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  duration_ms: number;
  results: Array<{
    id: string;
    name: string;
    layer: string;
    status: string;
    duration_ms: number;
  }>;
  quality_gate?: {
    run_id: string;
    status: string;
    passed: boolean;
    policy_name: string;
    pass_rate: number;
    violations: string[];
  };
}> {
  const res = await fetch(`${API_BASE}/qa/test-runner/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "Test runner execution failed");
  }
  return res.json();
}

export async function generateReleaseReport(payload: Record<string, unknown>): Promise<{
  run_id: string;
  status: string;
  report_markdown: string;
  events: Array<{
    timestamp: string;
    event_type: string;
    description: string;
  }>;
}> {
  const res = await fetch(`${API_BASE}/qa/reporting/release-report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "Release report generation failed");
  }
  return res.json();
}

export async function selfHealSelector(payload: {
  broken_selector: string;
  dom_snippet: string;
  failure_message?: string;
  target_action?: string;
}): Promise<{
  run_id: string;
  status: string;
  recommendation: {
    original_selector: string;
    failure_message: string;
    healed_selector: string;
    selector_type: string;
    confidence_score: number;
    resilience_rating: string;
    diagnosis: string;
    justification: string;
    code_replacement: string;
    alternatives: string[];
  };
}> {
  const res = await fetch(`${API_BASE}/qa/self-heal/selector`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "Self-healing selector failed");
  }
  return res.json();
}

export async function runStressTest(payload: {
  endpoint?: string;
  total_requests?: number;
  concurrency?: number;
}): Promise<{
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  duration_seconds: number;
  requests_per_second: number;
  p50_latency_ms: number;
  p90_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  min_latency_ms: number;
  max_latency_ms: number;
  avg_latency_ms: number;
  status_codes: Record<string, number>;
  error_summary: Record<string, number>;
}> {
  const res = await fetch(`${API_BASE}/qa/performance/stress-test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail ?? "Stress test benchmark failed");
  }
  return res.json();
}

export async function fetchAIProvidersStatus(): Promise<{
  active_provider: string;
  provider_abstraction_compliant: boolean;
  current_mode: string;
  providers: Record<
    string,
    {
      configured: boolean;
      key_preview: string | null;
      role: string;
    }
  >;
}> {
  const res = await fetch(`${API_BASE}/qa/ai/providers/status`);
  if (!res.ok) throw new Error("Failed to load AI providers status");
  return res.json();
}

export interface CapabilityItem {
  id: string;
  domain: string;
  feature: string;
  layer: string;
  priority: string;
  test_type: string;
  description: string;
  preconditions: string;
  expected_result: string;
  automation_status: string;
  production_safe: boolean;
  evidence_requirement: string;
  source_test: string;
  current_status: string;
}

export interface CatalogResponse {
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  capabilities: CapabilityItem[];
}

export interface CatalogSummary {
  total_capabilities: number;
  by_domain: Record<string, number>;
  by_layer: Record<string, number>;
  by_priority: Record<string, number>;
  active_domain: string;
}

export interface EvidenceRecord {
  test_id: string;
  domain: string;
  feature: string;
  layer: string;
  status: string;
  expected: string;
  actual: string;
  duration: number;
  environment: string;
  timestamp: string;
  agent: string;
  evidence: string;
  failure_reason?: string | null;
  defect_id?: string | null;
  commit_sha?: string | null;
}

export interface EvidenceLatestResponse {
  run_id: string;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  skipped_tests: number;
  pass_rate: number;
  total_duration_sec: number;
  timestamp: string;
  environment: string;
  commit_sha: string;
  filtered_count: number;
  records: EvidenceRecord[];
}

export async function fetchQACatalog(params?: {
  domain?: string;
  layer?: string;
  priority?: string;
  search?: string;
  page?: number;
  limit?: number;
}): Promise<CatalogResponse> {
  const query = new URLSearchParams();
  if (params?.domain) query.set("domain", params.domain);
  if (params?.layer) query.set("layer", params.layer);
  if (params?.priority) query.set("priority", params.priority);
  if (params?.search) query.set("search", params.search);
  if (params?.page) query.set("page", String(params.page));
  if (params?.limit) query.set("limit", String(params.limit));

  const res = await fetch(`${API_BASE}/qa/catalog?${query.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch capability catalog");
  return res.json();
}

export async function fetchQACatalogSummary(): Promise<CatalogSummary> {
  const res = await fetch(`${API_BASE}/qa/catalog/summary`);
  if (!res.ok) throw new Error("Failed to fetch capability catalog summary");
  return res.json();
}

export async function fetchQAEvidenceLatest(params?: {
  limit?: number;
  domain?: string;
  status?: string;
  layer?: string;
}): Promise<EvidenceLatestResponse> {
  const query = new URLSearchParams();
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.domain) query.set("domain", params.domain);
  if (params?.status) query.set("status", params.status);
  if (params?.layer) query.set("layer", params.layer);

  const res = await fetch(`${API_BASE}/qa/evidence/latest?${query.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch latest QA evidence");
  return res.json();
}

export interface OrchestratorPhase {
  phase_name: string;
  status: string;
  duration_ms: number;
  details?: Record<string, unknown>;
}

export interface OrchestratorReport {
  run_id: string;
  overall_status: string;
  total_duration_sec: number;
  total_capabilities: number;
  executed_tests: number;
  passed_tests: number;
  failed_tests: number;
  security_status: string;
  quality_gate_status: string;
  defects_found: number;
  defects_fixed: number;
  phases: OrchestratorPhase[];
}

export async function triggerOrchestratorRun(payload: {
  policy_name?: string;
  filter_domain?: string;
  target_defect?: string;
  include_ui?: boolean;
}): Promise<OrchestratorReport> {
  const res = await fetch(`${API_BASE}/qa/orchestrator/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to trigger orchestrator run");
  }
  return res.json();
}

// ============================================================================
// Phase 1B: Healthcare Clinical REST APIs
// ============================================================================

export async function fetchHealthcarePatients(): Promise<HealthcarePatient[]> {
  const res = await fetch(`${API_BASE}/healthcare/patients`, {
    headers: authenticatedHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to fetch healthcare patients");
  }
  return res.json();
}

export async function fetchHealthcarePatient(
  patientId: string,
  userRole?: string,
  simulateDefect?: string
): Promise<HealthcarePatient> {
  const headers = authenticatedHeaders();
  if (userRole) headers.set("X-User-Role", userRole);
  if (simulateDefect) headers.set("X-Simulate-Defect", simulateDefect);

  const res = await fetch(`${API_BASE}/healthcare/patients/${encodeURIComponent(patientId)}`, {
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Failed to fetch patient ${patientId}`);
  }
  return res.json();
}

export async function createHealthcarePatient(
  patientData: Record<string, unknown>,
  simulateDefect?: string
): Promise<HealthcarePatient> {
  const headers = authenticatedHeaders({ "Content-Type": "application/json" });
  if (simulateDefect) headers.set("X-Simulate-Defect", simulateDefect);

  const res = await fetch(`${API_BASE}/healthcare/patients`, {
    method: "POST",
    headers,
    body: JSON.stringify(patientData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to create patient");
  }
  return res.json();
}

export async function fetchHealthcarePractitioners(): Promise<HealthcarePractitioner[]> {
  const res = await fetch(`${API_BASE}/healthcare/practitioners`);
  if (!res.ok) throw new Error("Failed to fetch practitioners");
  return res.json();
}

export async function recordHealthcareObservation(
  observationData: Record<string, unknown>
): Promise<HealthcareObservation> {
  const headers = authenticatedHeaders({ "Content-Type": "application/json" });
  const res = await fetch(`${API_BASE}/healthcare/observations`, {
    method: "POST",
    headers,
    body: JSON.stringify(observationData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to record observation");
  }
  return res.json();
}

export async function fetchHealthcareObservations(patientId?: string): Promise<HealthcareObservation[]> {
  let url = `${API_BASE}/healthcare/observations`;
  if (patientId) {
    url += `?patient_id=${encodeURIComponent(patientId)}`;
  }
  const res = await fetch(url, {
    headers: authenticatedHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to fetch observations");
  }
  return res.json();
}

export async function scheduleHealthcareAppointment(
  appointmentData: Record<string, unknown>,
  simulateDefect?: string
): Promise<HealthcareAppointment> {
  const headers = authenticatedHeaders({ "Content-Type": "application/json" });
  if (simulateDefect) headers.set("X-Simulate-Defect", simulateDefect);

  const res = await fetch(`${API_BASE}/healthcare/appointments`, {
    method: "POST",
    headers,
    body: JSON.stringify(appointmentData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to schedule appointment");
  }
  return res.json();
}

export async function fetchHealthcareAppointments(): Promise<HealthcareAppointment[]> {
  const res = await fetch(`${API_BASE}/healthcare/appointments`, {
    headers: authenticatedHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to fetch appointments");
  }
  return res.json();
}

export async function calculatePediatricDosage(
  payload: PediatricDosageRequest,
  simulateDefect?: string
): Promise<PediatricDosageResponse> {
  const headers = new Headers({ "Content-Type": "application/json" });
  if (simulateDefect) headers.set("X-Simulate-Defect", simulateDefect);

  const res = await fetch(`${API_BASE}/healthcare/dosage/calculate`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Dosage calculation failed");
  }
  return res.json();
}

export async function fetchHealthcareDefects(): Promise<DefectSummary[]> {
  const res = await fetch(`${API_BASE}/healthcare/defects`);
  if (!res.ok) throw new Error("Failed to load healthcare defects");
  return res.json();
}

// ============================================================================
// Phase 1B: FinTech & Digital Banking REST APIs
// ============================================================================

export async function fetchFintechAccounts(): Promise<BankAccount[]> {
  const res = await fetch(`${API_BASE}/fintech/accounts`, {
    headers: authenticatedHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to fetch fintech accounts");
  }
  return res.json();
}

export async function createFintechAccount(account: BankAccount): Promise<BankAccount> {
  const res = await fetch(`${API_BASE}/fintech/accounts`, {
    method: "POST",
    headers: authenticatedHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(account),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to create fintech account");
  }
  return res.json();
}

export async function fetchFintechAccount(
  accountId: string,
  userRole?: string,
  simulateDefect?: string
): Promise<BankAccount> {
  const headers = authenticatedHeaders();
  if (userRole) headers.set("X-User-Role", userRole);
  if (simulateDefect) headers.set("X-Simulate-Defect", simulateDefect);

  const res = await fetch(`${API_BASE}/fintech/accounts/${encodeURIComponent(accountId)}`, {
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Failed to fetch account ${accountId}`);
  }
  return res.json();
}

export async function fetchFintechTransactions(accountId: string): Promise<LedgerTransaction[]> {
  const res = await fetch(`${API_BASE}/fintech/transactions/${encodeURIComponent(accountId)}`, {
    headers: authenticatedHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to fetch account transactions");
  }
  return res.json();
}

export async function executeFintechTransfer(
  payload: {
    source_account_id: string;
    destination_account_id: string;
    amount: number;
  },
  simulateDefect?: string
): Promise<LedgerTransaction> {
  const headers = authenticatedHeaders({ "Content-Type": "application/json" });
  if (simulateDefect) headers.set("X-Simulate-Defect", simulateDefect);

  const res = await fetch(`${API_BASE}/fintech/transfers`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Transfer execution failed");
  }
  return res.json();
}

export async function submitFintechSwiftTransfer(
  payload: ISO20022CreditTransfer
): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/fintech/transfers/swift`, {
    method: "POST",
    headers: authenticatedHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "SWIFT transfer failed");
  }
  return res.json();
}

export async function verifyFintechKYC(
  payload: KYCVerificationRequest
): Promise<KYCVerificationResponse> {
  const res = await fetch(`${API_BASE}/fintech/kyc/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    const message = Array.isArray(detail)
      ? detail
          .map((issue: { loc?: unknown[]; msg?: string }) =>
            `${Array.isArray(issue.loc) ? issue.loc.join(".") : "KYC"}: ${issue.msg ?? "Invalid value"}`
          )
          .join("; ")
      : typeof detail === "string"
        ? detail
        : "KYC verification failed";
    throw new Error(message);
  }
  return res.json();
}

export async function evaluateFintechFraud(
  payload: FraudEvaluationRequest,
  simulateDefect?: string
): Promise<FraudEvaluationResponse> {
  const headers = new Headers({ "Content-Type": "application/json" });
  if (simulateDefect) headers.set("X-Simulate-Defect", simulateDefect);

  const res = await fetch(`${API_BASE}/fintech/fraud/evaluate`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Fraud evaluation failed");
  }
  return res.json();
}

export async function fetchFintechDefects(): Promise<DefectSummary[]> {
  const res = await fetch(`${API_BASE}/fintech/defects`);
  if (!res.ok) throw new Error("Failed to load fintech defects");
  return res.json();
}

// ============================================================================
// Phase 1B: E-Commerce Retail REST APIs
// ============================================================================

export async function fetchEcommerceProducts(category?: string, inStockOnly = false): Promise<EcommerceProduct[]> {
  let url = `${API_BASE}/ecommerce/products?in_stock_only=${inStockOnly}`;
  if (category) {
    url += `&category=${encodeURIComponent(category)}`;
  }
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to fetch products");
  }
  return res.json();
}

export async function validateEcommerceCart(
  payload: {
    items: CartItem[];
    shipping_tier?: string;
    promo_code?: string;
  },
  simulateDefect?: string
): Promise<CartValidationResult> {
  const headers = new Headers({ "Content-Type": "application/json" });
  if (simulateDefect) headers.set("X-Simulate-Defect", simulateDefect);

  const res = await fetch(`${API_BASE}/ecommerce/cart/validate`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Cart validation failed");
  }
  return res.json();
}

export async function processEcommerceCheckout(
  payload: {
    cart_id?: string;
    customer_id: string;
    customer_email: string;
    items: CartItem[];
    shipping_tier: string;
    shipping_address: Record<string, string>;
    payment_method?: string;
    promo_code?: string;
    client_asserted_total?: number;
  },
  simulateDefect?: string
): Promise<{
  order_id: string;
  status: string;
  total_amount: number;
  payment_authorized: boolean;
  defect_injected?: string;
}> {
  const headers = authenticatedHeaders({ "Content-Type": "application/json" });
  if (simulateDefect) headers.set("X-Simulate-Defect", simulateDefect);

  const res = await fetch(`${API_BASE}/ecommerce/checkout`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detailMsg = Array.isArray(err.detail)
      ? err.detail
          .map((d: Record<string, unknown>) =>
            typeof d?.msg === "string" ? d.msg : JSON.stringify(d)
          )
          .join(", ")
      : typeof err.detail === "object"
      ? JSON.stringify(err.detail)
      : err.detail;
    throw new Error(detailMsg ?? "Checkout failed");
  }
  return res.json();
}

export async function fetchEcommerceOrders(): Promise<EcommerceOrder[]> {
  const res = await fetch(`${API_BASE}/ecommerce/orders`, {
    headers: authenticatedHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to fetch orders");
  }
  return res.json();
}

export async function fetchEcommerceOrder(orderId: string): Promise<EcommerceOrder> {
  const res = await fetch(`${API_BASE}/ecommerce/orders/${encodeURIComponent(orderId)}`, {
    headers: authenticatedHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Failed to fetch order ${orderId}`);
  }
  return res.json();
}

export async function updateEcommerceOrderStatus(
  orderId: string,
  status: string,
  simulateDefect?: string
): Promise<{ order_id: string; previous_status: string; new_status: string; state_desync_injected?: boolean }> {
  const headers = authenticatedHeaders({ "Content-Type": "application/json" });
  if (simulateDefect) headers.set("X-Simulate-Defect", simulateDefect);

  const res = await fetch(`${API_BASE}/ecommerce/orders/${encodeURIComponent(orderId)}/status`, {
    method: "PUT",
    headers,
    body: JSON.stringify({ status }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to update order status");
  }
  return res.json();
}

export async function processEcommerceRefund(
  payload: {
    return_id: string;
    order_id: string;
    sku?: string;
    quantity?: number;
    reason?: string;
    amount: number;
  },
  simulateDefect?: string
): Promise<RefundDisbursement> {
  const headers = authenticatedHeaders({ "Content-Type": "application/json" });
  if (simulateDefect) headers.set("X-Simulate-Defect", simulateDefect);

  const res = await fetch(`${API_BASE}/ecommerce/refunds`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Refund processing failed");
  }
  return res.json();
}

export async function fetchEcommerceDefects(): Promise<DefectSummary[]> {
  const res = await fetch(`${API_BASE}/ecommerce/defects`);
  if (!res.ok) throw new Error("Failed to load e-commerce defects");
  return res.json();
}

// ============================================================================
// Phase 1B: Telecom / 5G Mobile & BSS REST APIs
// ============================================================================

export async function fetchTelecomPlans(): Promise<TelecomPlan[]> {
  const res = await fetch(`${API_BASE}/telecom/plans`);
  if (!res.ok) throw new Error("Failed to load telecom plans");
  return res.json();
}

export async function createTelecomSubscriber(subscriber: TelecomSubscriber): Promise<TelecomSubscriber> {
  const res = await fetch(`${API_BASE}/telecom/subscribers`, {
    method: "POST",
    headers: authenticatedHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(subscriber),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to provision subscriber");
  }
  return res.json();
}

export async function fetchTelecomSubscriber(msisdn: string, simulateDefect?: string): Promise<TelecomSubscriber> {
  const headers = authenticatedHeaders();
  if (simulateDefect) headers.set("X-Simulate-Defect", simulateDefect);

  const res = await fetch(`${API_BASE}/telecom/subscribers/${encodeURIComponent(msisdn)}`, {
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Failed to fetch subscriber ${msisdn}`);
  }
  return res.json();
}

export async function fetchTelecomSubscriberCDRs(msisdn: string): Promise<CallDetailRecord[]> {
  const res = await fetch(`${API_BASE}/telecom/subscribers/${encodeURIComponent(msisdn)}/cdrs`, {
    headers: authenticatedHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to fetch subscriber CDRs");
  }
  return res.json();
}

export async function updateTelecomSubscriberStatus(
  msisdn: string,
  targetStatus: string,
  simulateDefect?: string
): Promise<TelecomSubscriber> {
  const headers = authenticatedHeaders({ "Content-Type": "application/json" });
  if (simulateDefect) headers.set("X-Simulate-Defect", simulateDefect);

  const res = await fetch(`${API_BASE}/telecom/subscribers/${encodeURIComponent(msisdn)}/status`, {
    method: "POST",
    headers,
    body: JSON.stringify({ target_status: targetStatus }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to transition subscriber status");
  }
  return res.json();
}

export async function executeTelecomSimSwap(
  msisdn: string,
  payload: { new_iccid: string; new_imsi: string },
  simulateDefect?: string
): Promise<{
  status: string;
  new_iccid?: string;
  old_iccid_deactivated?: boolean;
  twin_sim_active?: boolean;
}> {
  const headers = authenticatedHeaders({ "Content-Type": "application/json" });
  if (simulateDefect) headers.set("X-Simulate-Defect", simulateDefect);

  const res = await fetch(`${API_BASE}/telecom/subscribers/${encodeURIComponent(msisdn)}/sim-swap`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "SIM swap execution failed");
  }
  return res.json();
}

export async function rateTelecomCDR(
  cdr: CallDetailRecord,
  simulateDefect?: string
): Promise<RateCDRResponse> {
  const headers = authenticatedHeaders({ "Content-Type": "application/json" });
  if (simulateDefect) headers.set("X-Simulate-Defect", simulateDefect);

  const res = await fetch(`${API_BASE}/telecom/cdr/rate`, {
    method: "POST",
    headers,
    body: JSON.stringify({ cdr }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "CDR rating failed");
  }
  return res.json();
}

export async function fetchTelecomDefects(): Promise<DefectSummary[]> {
  const res = await fetch(`${API_BASE}/telecom/defects`);
  if (!res.ok) throw new Error("Failed to load telecom defects");
  return res.json();
}
