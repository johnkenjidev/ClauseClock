// Synthetic, read-only demo workspace (Stage 5). No auth, no backend, no real
// data. Dates are derived from the viewer's current date so the urgent
// finding stays exactly 11 days out. Findings match the real Stage 1-4 shape
// so the existing FindingCard renders them unchanged.

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

  // --- URGENT: automatic renewal, 60-day notice, deadline 11 days out ---
  const urgentDeadline = addDays(today, 11);              // effective_action_deadline
  const urgentRenewal = addDays(urgentDeadline, 60);      // next_renewal_date
  const urgentEffective = addDays(urgentRenewal, -365);   // one year prior
  const urgent = {
    id: "demo_f_urgent", type: "renewal_notice", state: "unconfirmed",
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
      next_renewal_date: iso(urgentRenewal),
      action_deadline: iso(urgentDeadline),
      earliest_action_date: null,
      effective_action_deadline: iso(urgentDeadline),
      days_remaining: 11,
    },
    sources: [
      src("renewal_term",
        "This Agreement shall commence on the Effective Date and continue for an initial term of twelve (12) months, and shall automatically renew for successive twelve (12) month terms.",
        "p.4"),
      src("notice_period",
        "unless either party provides written notice of non-renewal not less than sixty (60) days prior to the end of the then-current term.",
        "p.4"),
      src("notice_method",
        "All notices required under this Agreement shall be in writing and delivered by certified mail, return receipt requested.",
        "p.12"),
      src("notice_recipient",
        "Notices to Northwind shall be addressed to the General Counsel, Northwind Corp, 200 Harbor Way, Boston, MA.",
        "p.12"),
    ],
    plain_english:
      "Your Northwind CRM subscription renews automatically for another 12 months unless you send a written non-renewal notice by certified mail at least 60 days before the term ends.",
    why_it_matters:
      `If notice is not received by ${iso(urgentDeadline)}, the agreement renews for another 12-month term at $48,000. You have 11 days left to act.`,
    suggested_action:
      `To avoid the renewal, send written notice of non-renewal by certified mail to the General Counsel, Northwind Corp, so it is received on or before ${iso(urgentDeadline)}.`,
  };

  // --- calm validated (money, far out) ---
  const atlasDeadline = addDays(today, 184);
  const atlasRenewal = addDays(atlasDeadline, 90);
  const atlas = {
    id: "demo_f_atlas", type: "renewal_notice", state: "unconfirmed",
    validation_status: "validated", confidence: "high", action_required: true,
    money_amount: 120000, money_currency: "USD", money_kind: "contract_value",
    rank_category: "risk", rank_score: 1_181_600,
    extracted: {
      renewal_type: "automatic", effective_date: iso(addDays(atlasRenewal, -1095)),
      initial_term_value: 36, initial_term_unit: "months",
      renewal_period_value: 12, renewal_period_unit: "months",
      notice_days_min: 90, notice_days_max: null, notice_basis: "calendar",
      notice_measured_to: "sent", notice_method: "written notice", notice_recipient: "Atlas Cloud, Contracts Team",
      next_renewal_date: iso(atlasRenewal), action_deadline: iso(atlasDeadline),
      earliest_action_date: null, effective_action_deadline: iso(atlasDeadline),
      days_remaining: 184,
    },
    sources: [
      src("renewal_term", "This Order Form renews automatically for additional one (1) year terms.", "p.2"),
      src("notice_period", "unless written notice is provided not less than ninety (90) days before the renewal date.", "p.2"),
    ],
    plain_english: "Atlas hosting renews automatically each year unless you give 90 days' written notice before the renewal date.",
    why_it_matters: `The next renewal is ${iso(atlasRenewal)} at $120,000. You have well over 90 days, so there is time to review.`,
    suggested_action: `If you may not renew, plan to send written notice before ${iso(atlasDeadline)}.`,
  };

  // --- calm validated (nearer, pending tone) ---
  const meridianDeadline = addDays(today, 47);
  const meridianRenewal = addDays(meridianDeadline, 30);
  const meridian = {
    id: "demo_f_meridian", type: "renewal_notice", state: "unconfirmed",
    validation_status: "validated", confidence: "medium", action_required: true,
    money_amount: 26400, money_currency: "USD", money_kind: "contract_value",
    rank_category: "risk", rank_score: 1_195_300,
    extracted: {
      renewal_type: "automatic", effective_date: iso(addDays(meridianRenewal, -365)),
      initial_term_value: 12, initial_term_unit: "months",
      renewal_period_value: 12, renewal_period_unit: "months",
      notice_days_min: 30, notice_days_max: null, notice_basis: "calendar",
      notice_measured_to: "sent", notice_method: "email to account manager", notice_recipient: "Meridian account manager",
      next_renewal_date: iso(meridianRenewal), action_deadline: iso(meridianDeadline),
      earliest_action_date: null, effective_action_deadline: iso(meridianDeadline),
      days_remaining: 47,
    },
    sources: [
      src("renewal_term", "The subscription will renew automatically for successive annual terms.", "p.3"),
      src("notice_period", "unless notice is given at least thirty (30) days prior to renewal.", "p.3"),
    ],
    plain_english: "Meridian renews automatically each year with a 30-day notice requirement.",
    why_it_matters: `Renewal is ${iso(meridianRenewal)} at $26,400; the 30-day notice window is approaching.`,
    suggested_action: `Decide before ${iso(meridianDeadline)} whether to renew or send notice.`,
  };

  // --- needs_review (missing effective date) ---
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

  // --- informational (manual / does not auto-renew) ---
  const cedar = {
    id: "demo_f_cedar", type: "renewal_notice", state: "unconfirmed",
    validation_status: "validated", confidence: "high", action_required: false,
    money_amount: 18000, money_currency: "USD", money_kind: "contract_value",
    rank_category: "informational", rank_score: 1_018_000,
    extracted: {
      renewal_type: "manual", effective_date: iso(addDays(today, -300)),
      initial_term_value: 24, initial_term_unit: "months",
      renewal_period_value: null, renewal_period_unit: null,
      notice_days_min: null, notice_days_max: null, notice_basis: null,
      notice_method: null, notice_recipient: null,
      next_renewal_date: null, action_deadline: null, earliest_action_date: null,
      effective_action_deadline: null, days_remaining: null,
    },
    sources: [
      src("renewal_term", "This Agreement does not renew automatically; any renewal requires a mutually signed written extension.", "p.6"),
    ],
    plain_english: "This facilities agreement does not auto-renew — it only continues if both parties sign a written extension.",
    why_it_matters: "There is no automatic renewal deadline to miss; no action is required to avoid a renewal.",
    suggested_action: "No deadline action needed. Revisit only if you wish to extend the agreement.",
  };

  const contracts = [
    { id: "demo_c_northwind", name: "Northwind CRM — SaaS Subscription", counterparty: "Northwind Corp", annual_value: 48000, currency: "USD", status: "analysed", findings: [urgent] },
    { id: "demo_c_meridian", name: "Meridian Data Processing Agreement", counterparty: "Meridian Systems", annual_value: 26400, currency: "USD", status: "analysed", findings: [meridian] },
    { id: "demo_c_atlas", name: "Atlas Cloud Hosting Order Form", counterparty: "Atlas Cloud", annual_value: 120000, currency: "USD", status: "analysed", findings: [atlas] },
    { id: "demo_c_harbor", name: "Harbor Logistics Master Services Agreement", counterparty: "Harbor Logistics", annual_value: 30000, currency: "USD", status: "analysed", findings: [harbor] },
    { id: "demo_c_cedar", name: "Cedar Facilities Management Agreement", counterparty: "Cedar Facilities", annual_value: 18000, currency: "USD", status: "analysed", findings: [cedar] },
  ];

  // What Matters: every finding + its contract, sorted by rank_score desc.
  const whatMatters = contracts
    .flatMap((c) => c.findings.map((f) => ({ finding: f, contract: c })))
    .sort((a, b) => b.finding.rank_score - a.finding.rank_score);

  return { contracts, whatMatters };
}
