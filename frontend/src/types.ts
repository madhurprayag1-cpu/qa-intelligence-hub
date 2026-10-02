export type Airport = {
  id: number;
  code: string;
  name: string;
  city: string;
  country: string;
  timezone: string;
  active: boolean;
};

export type Airline = {
  id: number;
  code: string;
  name: string;
  country: string;
  active: boolean;
};

export type Flight = {
  flight_id: number;
  flight_number: string;
  airline: string;
  origin: string;
  destination: string;
  departure_time: string;
  arrival_time: string;
  duration_minutes: number;
  available_seats: number;
  base_price: number;
};

export type FlightListItem = {
  id: number;
  flight_number: string;
  airline: { code: string; name: string };
  origin: { code: string; name: string; city: string };
  destination: { code: string; name: string; city: string };
  departure_time: string;
  arrival_time: string;
  duration_minutes: number;
  total_seats: number;
  available_seats: number;
  base_price: number;
  active: boolean;
};

export type AncillaryOption = {
  id: string | number;
  name: string;
  price: number;
  unit?: string;
};

export type AncillaryCatalog = {
  baggage: AncillaryOption[];
  seats: AncillaryOption[];
  meals: AncillaryOption[];
};

export type AncillarySelection = {
  baggage_tier: number;
  seat_preference: string;
  meal_preference: string;
};

export type AncillaryItem = {
  id?: string;
  name?: string;
  price?: number;
  category?: string;
  [key: string]: unknown;
};

export type Booking = {
  id: number;
  reference: string;
  flight_id: number;
  passenger_name: string;
  passenger_email: string;
  seats: number;
  base_fare?: number;
  ancillary_amount?: number;
  total_amount: number;
  status: string;
  ancillaries?: Record<string, AncillaryItem | undefined>;
};

export type PaymentMethod =
  | "CREDIT_CARD_3DS"
  | "CREDIT_CARD"
  | "DEBIT_CARD"
  | "UPI"
  | "WALLET"
  | "EASY_PAY"
  | "CASH";

export type ThreeDSStatus =
  | "NOT_REQUIRED"
  | "PENDING"
  | "SUCCESS"
  | "FAILED"
  | "TIMEOUT"
  | "CANCELLED";

export type PaymentResponse = {
  id: number;
  booking_id: number;
  amount: number | string;
  currency: string;
  method: string;
  status: string;
  three_ds_required: boolean;
  three_ds_status: string;
  authorization_status: string;
  transaction_reference: string | null;
  provider_reference: string | null;
  failure_code: string | null;
  failure_reason: string | null;
  retry_count: number;
};

export type HealthStatus = {
  status: string;
  service: string;
  version: string;
};

export type DefectSummary = {
  id: string;
  name: string;
  category: string;
  affected_endpoint: string;
  description: string;
  how_to_reproduce: string;
  expected_qa_detection: string;
  headers: Record<string, string>;
};

export type AIProviderInfo = {
  provider: string;
  default_model: string;
  mock_active: boolean;
};

export type RAGQueryResponse = {
  answer: string;
  citations: Array<{ chunk_id: string; source: string; score: number }>;
  groundedness_score: number;
  provider: string;
};

export type RCAResponse = {
  summary: string;
  root_cause: string;
  severity: string;
  affected_component: string;
  recommended_fix: string;
  provider: string;
};

export type QualityGateResponse = {
  run_id?: string;
  passed: boolean;
  status: string;
  policy_name: string;
  pass_rate: number;
  failure_rate: number;
  total: number;
  passed_tests: number;
  failed_tests: number;
  skipped: number;
  violations: string[];
  signals: Record<string, unknown>;
  evaluated_at: string;
};

export type SecurityAuditFinding = {
  category?: string;
  severity?: string;
  description?: string;
  remediation?: string;
  field?: string;
  location?: string;
  [key: string]: unknown;
};

export type SecurityAuditReport = {
  status?: string;
  pci_dss_compliant?: boolean;
  sanitization_status?: string;
  findings?: SecurityAuditFinding[];
  summary?: string;
  risk_level?: string;
  [key: string]: unknown;
};

export type SecurityAuditResult = {
  endpoint?: string;
  role?: string;
  status?: string;
  report?: SecurityAuditReport;
  [key: string]: unknown;
};

export type QALayerMeta = {
  id: string;
  name: string;
  path: string;
  test_count: number;
  description: string;
  layer_type: string;
};

export type RegressionPlan = {
  changed_files: string[];
  selected_test_files: string[];
  selected_tags: string[];
  pytest_command: string;
  playwright_command: string | null;
  reasoning: string[];
  test_count: number;
};

export type TestRunnerSpecResult = {
  id: string;
  name: string;
  layer: string;
  status: string;
  duration_ms: number;
};

export type TestRunnerResult = {
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  duration_ms: number;
  results: TestRunnerSpecResult[];
  quality_gate?: {
    run_id: string;
    status: string;
    passed: boolean;
    policy_name: string;
    pass_rate: number;
    violations: string[];
  };
};

export type ReleaseReportResult = {
  run_id: string;
  status: string;
  report_markdown: string;
  events: Array<{
    timestamp: string;
    event_type: string;
    description: string;
  }>;
};

export type SelfHealRecommendation = {
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

export type SelfHealResponse = {
  run_id: string;
  status: string;
  recommendation: SelfHealRecommendation;
};

export type LoadBenchmarkData = {
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
};

export type AIProviderStatusData = {
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
};

// ==========================================
// Phase 1B: Healthcare Domain Types
// ==========================================
export type HealthcarePatient = {
  id: string;
  mrn?: string;
  resourceType?: string;
  active?: boolean;
  first_name?: string;
  last_name?: string;
  name?: Array<{ family: string; given: string[] }>;
  gender: string;
  birthDate?: string;
  dob?: string;
  phone?: string;
  phone_masked?: string;
  email?: string;
  telecom?: Array<{ system: string; value: string }>;
  ssn_masked?: string;
  ssn_raw?: string;
  owner_user_id?: number;
};

export type HealthcarePractitioner = {
  id: string;
  name: string;
  specialty: string;
};

export type HealthcareObservation = {
  id?: string;
  resourceType?: string;
  status: string;
  patient_id?: string;
  code: {
    coding: Array<{
      code: string;
      display: string;
      system?: string;
    }>;
  };
  subject?: { reference: string };
  effectiveDateTime?: string;
  valueQuantity?: {
    value: number;
    unit: string;
  };
};

export type HealthcareAppointment = {
  id?: string;
  resourceType?: string;
  status: string;
  start: string;
  end: string;
  participant: Array<{
    actor: { reference: string };
    status: string;
  }>;
};

export type PediatricDosageRequest = {
  patient_id: string;
  drug_name: string;
  patient_weight_kg: number;
  recommended_mg_per_kg: number;
  frequency_hours: number;
};

export type PediatricDosageResponse = {
  patient_id: string;
  drug_name: string;
  patient_weight_kg: number;
  recommended_mg_per_kg: number;
  single_dose_mg: number;
  daily_total_mg: number;
  frequency_hours: number;
  precision_verified: boolean;
  warning?: string | null;
};

// ==========================================
// Phase 1B: FinTech Domain Types
// ==========================================
export type BankAccount = {
  account_id: string;
  account_holder: string;
  email: string;
  iban: string;
  bic_swift: string;
  currency: string;
  balance: number;
  account_type: string;
  kyc_tier: string;
  is_active: boolean;
};

export type LedgerTransaction = {
  transaction_id: string;
  timestamp?: string;
  created_at?: string;
  source_account_id: string;
  destination_account_id: string;
  amount: number;
  currency: string;
  description?: string;
  source_new_balance?: number;
  dest_new_balance?: number;
  status: string;
};

export type KYCVerificationRequest = {
  customer_id: string;
  full_name: string;
  date_of_birth: string;
  tax_id_masked: string;
  monthly_income: number;
};

export type KYCVerificationResponse = {
  customer_id: string;
  full_name: string;
  assigned_tier: string;
  daily_transfer_limit: number;
  pep_sanctions_cleared: boolean;
  status: string;
  review_reason?: string | null;
};

export type FraudEvaluationRequest = {
  account_id: string;
  amount: number;
  currency?: string;
  origin_country: string;
  destination_country: string;
  transactions_in_last_minute: number;
};

export type FraudEvaluationResponse = {
  account_id: string;
  risk_score: number;
  action: "ALLOW" | "CHALLENGE_2FA" | "BLOCK";
  detected_anomalies: string[];
};

export type ISO20022CreditTransfer = {
  message_id: string;
  instruction_id: string;
  debtor_iban: string;
  creditor_iban: string;
  instructed_amount: number;
  instructed_currency: string;
};

// ==========================================
// Phase 1B: E-Commerce Domain Types
// ==========================================
export type EcommerceProduct = {
  sku: string;
  name: string;
  category: string;
  price: number;
  stock_quantity: number;
  is_active: boolean;
};

export type CartItem = {
  sku: string;
  name: string;
  product_name?: string;
  quantity: number;
  unit_price: number;
};

export type CartTotals = {
  subtotal: number;
  discount_amount: number;
  shipping_cost: number;
  tax_amount: number;
  total_amount: number;
};

export type CartValidationResult = {
  valid: boolean;
  items_count: number;
  totals: CartTotals;
  applied_promo?: string | null;
  stale_cache_drift?: boolean;
};

export type EcommerceOrder = {
  order_id: string;
  customer_id?: string;
  customer_email?: string;
  status: string;
  total_amount: number;
  items: CartItem[];
  created_at?: string;
  tracking_number?: string;
  shipping_tier?: string;
  shipping_address?: Record<string, string>;
};

export type RefundDisbursement = {
  refund_id: string;
  return_id: string;
  order_id: string;
  disbursed_amount: number;
  processed_at: string;
  duplicate_credit?: boolean;
};

// ==========================================
// Phase 1B: Telecom Domain Types
// ==========================================
export type TelecomPlan = {
  plan_id: string;
  name: string;
  plan_type: string;
  monthly_fee: number;
  voice_minutes_included: number;
  sms_included: number;
  data_gb_included: number;
  fup_threshold_gb: number;
  overage_voice_per_min: number;
  overage_data_per_mb: number;
  roaming_enabled: boolean;
  throttle_speed_kbps: number;
};

export type TelecomSubscriber = {
  subscriber_id?: string;
  msisdn: string;
  sim: {
    iccid: string;
    imsi: string;
    is_esim?: boolean;
    is_active?: boolean;
    puk_code?: string;
  };
  plan: TelecomPlan;
  status: string;
  balance: number;
  minutes_used?: number;
  sms_used?: number;
  data_used_mb?: number;
  roaming_allowed: boolean;
  kyc_verified?: boolean;
  created_at?: string;
  _diagnostic_trace?: Record<string, unknown>;
};

export type CallDetailRecord = {
  cdr_id: string;
  msisdn: string;
  destination: string;
  call_type: string;
  zone: string;
  duration_seconds: number;
  bytes_transferred: number;
  rated_amount?: number;
  billed?: boolean;
  created_at?: string;
};

export type RateCDRResponse = {
  cdr_id: string;
  msisdn: string;
  rated_amount: number;
  billed: boolean;
  status: string;
  balance_remaining: number;
};
