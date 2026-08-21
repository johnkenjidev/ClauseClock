// Synthetic, read-only demo workspace. No auth, no backend, no real data.
// Dates float from the viewer's current date so the demo stays useful during
// judging. Shapes mirror production findings closely enough to reuse FindingCard.

const iso = (d) => {
  const x = new Date(d);
  return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, "0")}-${String(x.getDate()).padStart(2, "0")}`;
};
const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };

let _seq = 1000;
const src = (purpose, quote, location) => ({
  purpose, quote, location, char_offset: (_seq += 37), chunk_id: `c_${_seq}`,
  document_id: `demo_doc_${_seq}`,
});

export function buildDemoWorkspace(now = new Date()) {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  // Northwind — confirmed urgent renewal + price increase on the same contract.
  const urgentDeadline = addDays(today, 11);
  const urgentRenewal = addDays(urgentDeadline, 60);
  const urgentEffective = addDays(urgentRenewal, -365);
  const urgent = {
    id: "demo_f_urgent", type: "renewal_notice", state: "confirmed",
    validation_status: "validated", confidence: "high", action_required: true,
    money_amount: 48000, money_currency: "USD", money_kind: "contract_value",
    rank_category: "urgent", rank_score: 1_298_900,
    extracted: {
      renewal_type: "automatic", effective_date: iso(urgentEffective),
      initial_term_value: 12, initial_term_unit: "months",
      renewal_period_value: 12, renewal_period_unit: "months",
      notice_days_min: 60, notice_days_max: null, notice_basis: "calendar",
      business_day_definition: null, notice_measured_to: "received",
      deemed_receipt_rule: null,
      notice_method: "written notice by certified mail",
      notice_recipient: "General Counsel, Northwind Corp, 200 Harbor Way, Boston, MA",
      next_renewal_date: iso(urgentRenewal), action_deadline: iso(urgentDeadline),
      earliest_action_date: null, effective_action_deadline: iso(urgentDeadline),
      days_remaining: 11,
    },
    sources: [
      src("renewal_term", "This Agreement shall commence on the Effective Date and continue for an initial term of twelve (12) months, and shall automatically renew for successive twelve (12) month terms.", "p.4"),
      src("notice_period", "unless either party provides written notice of non-renewal not less than sixty (60) days prior to the end of the then-current term.", "p.4"),
      src("notice_method", "All notices required under this Agreement shall be in writing and delivered by certified mail, return receipt requested.", "p.12"),
      src("notice_recipient", "Notices to Northwind shall be addressed to the General Counsel, Northwind Corp, 200 Harbor Way, Boston, MA.", "p.12"),
    ],
    plain_english: "Your Northwind CRM subscription renews automatically for another 12 months unless you send a written non-renewal notice by certified mail at least 60 days before the term ends.",
    why_it_matters: `If notice is not received by ${iso(urgentDeadline)}, the agreement renews for another 12-month term at $48,000. You have 11 days left to act.`,
    suggested_action: `If you do not want the renewal, send written non-renewal notice by certified mail so it is received on or before ${iso(urgentDeadline)}.`,
  };

  const priceDeadline = addDays(today, 18);
  const priceChangeDate = addDays(priceDeadline, 30);
  const northwindPrice = {
    id: "demo_f_price", type: "price_increase", state: "corrected",
    validation_status: "validated", confidence: "high", action_required: true,
    money_amount: 1920, money_currency: "USD", money_kind: "cost",
    rank_category: "money", rank_score: 1_250_000,
    extracted: {
      increase_type: "fixed_automatic", increase_percent: 4,
      increase_amount: null, increase_formula: null,
      increase_basis: "annual subscription fee", next_term_amount: 49920,
      objection_window_value: 30, objection_window_unit: "days",
      objection_basis: "calendar", price_change_date: iso(priceChangeDate),
      objection_deadline: iso(priceDeadline), effective_action_deadline: iso(priceDeadline),
      days_remaining: 18,
    },
    sources: [
      src("increase", "Subscription Fees will increase by four percent (4%) at the start of each renewal term.", "Order Form §3"),
      src("objection", "Customer may object to the increase by written notice delivered at least thirty (30) days before the renewal date.", "Order Form §3"),
    ],
    plain_english: "The annual subscription fee rises 4% at renewal, from $48,000 to $49,920, unless you use the stated objection window.",
    why_it_matters: "The increase adds $1,920 for the next annual term and has its own response deadline.",
    suggested_action: `If you plan to object, send the contract-required written objection by ${iso(priceDeadline)}.`,
  };

  // Meridian — invoice dispute window with a deterministic deadline.
  const disputeDeadline = addDays(today, 24);
  const dispute = {
    id: "demo_f_dispute", type: "invoice_dispute", state: "confirmed",
    validation_status: "validated", confidence: "high", action_required: true,
    money_amount: 8500, money_currency: "USD", money_kind: "cost",
    rank_category: "urgent", rank_score: 1_220_000,
    extracted: {
      who: "Customer", window_value: 30, window_unit: "days", window_basis: "calendar",
      window_reference: "invoice receipt", trigger_date: iso(addDays(disputeDeadline, -30)),
      effective_action_deadline: iso(disputeDeadline), days_remaining: 24,
    },
    sources: [
      src("obligation", "Customer must notify Meridian in writing of any disputed invoice amount.", "MSA §7.4"),
      src("window", "Any invoice dispute must be received within thirty (30) days after receipt of the applicable invoice.", "MSA §7.4"),
      src("amount", "The disputed implementation invoice is $8,500.", "Order Form p.2"),
    ],
    plain_english: "You have 30 days from receiving the invoice to raise a written dispute.",
    why_it_matters: "Waiting past the contractual dispute window could make the $8,500 invoice harder to challenge under the agreement.",
    suggested_action: `Review the invoice and, if you dispute it, send written notice by ${iso(disputeDeadline)}.`,
  };

  // Atlas — a standing early-exit right that becomes actionable because both an
  // earliest exit date and notice period are known.
  const terminationDeadline = addDays(today, 72);
  const earliestTermination = addDays(terminationDeadline, 60);
  const termination = {
    id: "demo_f_termination", type: "termination_right", state: "confirmed",
    validation_status: "validated", confidence: "high", action_required: true,
    money_amount: 10000, money_currency: "USD", money_kind: "cost",
    rank_category: "money", rank_score: 1_180_000,
    extracted: {
      termination_type: "for_convenience", who_may_terminate: "Customer",
      notice_period_value: 60, notice_period_unit: "days", notice_basis: "calendar",
      cure_period_value: null, cure_period_unit: null,
      earliest_termination_date: iso(earliestTermination),
      termination_fee_amount: 10000,
      notice_method: "written notice", notice_recipient: "Atlas Cloud Legal",
      effective_action_deadline: iso(terminationDeadline), days_remaining: 72,
    },
    sources: [
      src("termination_right", "Customer may terminate this Order Form for convenience after the minimum commitment period.", "Order Form §8"),
      src("notice_period", "Termination for convenience requires at least sixty (60) days' prior written notice.", "Order Form §8"),
      src("termination_fee", "A termination charge of $10,000 applies to an early convenience termination.", "Order Form §8"),
    ],
    plain_english: "You have a contractual right to exit early for convenience with 60 days' written notice, subject to the stated $10,000 termination charge.",
    why_it_matters: "The right creates an alternative to staying through the full hosting term, but the notice date and termination charge matter.",
    suggested_action: `If you want the earliest available exit, decide and prepare written notice by ${iso(terminationDeadline)}.`,
  };

  // Harbor — intentionally unresolved so judges can see the product refuses to invent a date.
  const harbor = {
    id: "demo_f_harbor", type: "renewal_notice", state: "unconfirmed",
    validation_status: "needs_review", confidence: "medium", action_required: true,
    money_amount: 30000, money_currency: "USD", money_kind: "contract_value",
    rank_category: "risk", rank_score: 100000,
    extracted: {
      renewal_type: "automatic", effective_date: null,
      initial_term_value: null, initial_term_unit: null,
      renewal_period_value: 12, renewal_period_unit: "months",
      notice_days_min: 60, notice_days_max: null, notice_basis: "calendar",
      notice_method: "written notice", notice_recipient: "Harbor Logistics",
      next_renewal_date: null, action_deadline: null, earliest_action_date: null,
      effective_action_deadline: null, days_remaining: null,
    },
    sources: [
      src("renewal_term", "This MSA renews automatically for one-year terms unless terminated with sixty (60) days notice.", "p.5"),
      src("notice_period", "sixty (60) days notice", "p.5"),
    ],
    validation_notes: ["Confirm the effective date to calculate this deadline."],
    plain_english: null, why_it_matters: null, suggested_action: null,
  };

  // Cedar — a claim opportunity rather than another renewal.
  const creditDeadline = addDays(today, 39);
  const serviceCredit = {
    id: "demo_f_credit", type: "service_credit", state: "confirmed",
    validation_status: "validated", confidence: "high", action_required: true,
    money_amount: 3000, money_currency: "USD", money_kind: "opportunity",
    rank_category: "opportunity", rank_score: 1_150_000,
    extracted: {
      who: "Customer", window_value: 45, window_unit: "days", window_basis: "calendar",
      window_reference: "service-level failure", trigger_date: iso(addDays(creditDeadline, -45)),
      effective_action_deadline: iso(creditDeadline), days_remaining: 39,
    },
    sources: [
      src("obligation", "Customer is eligible for a service credit equal to ten percent (10%) of the affected monthly fee following a Severity 1 availability failure.", "SLA §4"),
      src("window", "Credit requests must be submitted within forty-five (45) days after the applicable service-level failure.", "SLA §4"),
      src("amount", "The maximum credit for the affected period is $3,000.", "SLA §4"),
    ],
    plain_english: "A qualifying service-level failure can support a service-credit claim, but the request must be submitted within 45 days.",
    why_it_matters: "The contract provides up to $3,000 of value that is easy to lose simply by missing the claim window.",
    suggested_action: `If the outage qualifies, collect the incident record and submit the credit request by ${iso(creditDeadline)}.`,
  };

  const contracts = [
    { id: "demo_c_northwind", name: "Northwind CRM — SaaS Subscription", counterparty: "Northwind Corp", annual_value: 48000, currency: "USD", status: "analysed", findings: [urgent, northwindPrice] },
    { id: "demo_c_meridian", name: "Meridian Data Processing Agreement", counterparty: "Meridian Systems", annual_value: 26400, currency: "USD", status: "analysed", findings: [dispute] },
    { id: "demo_c_atlas", name: "Atlas Cloud Hosting Order Form", counterparty: "Atlas Cloud", annual_value: 120000, currency: "USD", status: "analysed", findings: [termination] },
    { id: "demo_c_harbor", name: "Harbor Logistics Master Services Agreement", counterparty: "Harbor Logistics", annual_value: 30000, currency: "USD", status: "analysed", findings: [harbor] },
    { id: "demo_c_cedar", name: "Cedar Facilities Management Agreement", counterparty: "Cedar Facilities", annual_value: 36000, currency: "USD", status: "analysed", findings: [serviceCredit] },
  ];

  const whatMatters = contracts
    .flatMap((c) => c.findings.map((f) => ({ finding: f, contract: c })))
    .sort((a, b) => b.finding.rank_score - a.finding.rank_score);

  const actionItems = whatMatters
    .filter(({ finding }) =>
      finding.validation_status === "validated" &&
      finding.action_required &&
      finding.extracted?.effective_action_deadline &&
      ["confirmed", "corrected"].includes(finding.state)
    )
    .map(({ finding, contract }) => ({ ...finding, contract_name: contract.name }));

  return { contracts, whatMatters, actionItems };
}
