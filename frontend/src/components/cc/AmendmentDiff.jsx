// Amendment Diff — read-only comparison of a preserved superseded finding
// against its current replacement. Built entirely from already-stored
// extracted fields + validated sources (via /superseded-history). No new
// calculations, no LLM calls — pure client-side field comparison.
import { useState } from "react";
import { ChevronDown } from "lucide-react";

const GENERIC_TYPES = [
  "service_credit", "invoice_dispute", "notice_requirement",
  "fee_or_penalty", "rebate_or_refund", "warranty_claim",
];

const ANCHOR_LABEL = { term_end: "Term end", renewal_start: "Renewal start", unknown: "Unknown" };
const INCREASE_TYPE_LABEL = {
  fixed_automatic: "Fixed automatic", capped: "Capped (maximum)",
  formula: "Formula / index-linked", unspecified: "Unspecified",
};
const TERMINATION_TYPE_LABEL = {
  for_convenience: "For convenience", early_exit: "Early exit / break right",
  for_cause: "For cause only", unspecified: "Unspecified",
};
const ROLE_LABEL = {
  primary: "Primary agreement", amendment: "Amendment",
  order_form: "Order form", exhibit: "Exhibit", sla: "SLA",
};

function longDate(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US",
    { year: "numeric", month: "long", day: "numeric" });
}

function noticeText(e) {
  if (e.notice_days_min == null) return null;
  const basis = e.notice_basis === "business" ? "business days" : "days";
  return e.notice_days_max != null
    ? `${e.notice_days_min}\u2013${e.notice_days_max} ${basis}`
    : `${e.notice_days_min} ${basis}`;
}

// notice_recipient ONLY: treat two recipient strings as unchanged when they
// contain the same set of email addresses (case/order insensitive), e.g. a
// re-worded clause naming the same mailbox. No broad semantic normalization
// is applied to any other field — everything else stays a strict text diff.
function emailSetKey(text) {
  if (!text) return null;
  const emails = (text.match(/[\w.+-]+@[\w-]+\.[\w.-]+/gi) || []).map((s) => s.toLowerCase());
  if (!emails.length) return null;
  return [...new Set(emails)].sort().join(",");
}
function recipientUnchanged(before, after) {
  const b = emailSetKey(before);
  const a = emailSetKey(after);
  if (b == null || a == null) return false;
  return b === a;
}

// Field -> label + governing source purpose + formatter. Purposes are the
// SAME purpose strings already emitted by extraction (never invented here).
const FIELD_DEFS = {
  renewal_notice: [
    { label: "Effective date", purpose: "effective_date", fmt: (e) => longDate(e.effective_date) },
    { label: "Renewal type", purpose: "renewal_term",
      fmt: (e) => (e.renewal_type === "automatic" ? "Automatic" : e.renewal_type || null) },
    { label: "Renewal period", purpose: "renewal_term",
      fmt: (e) => (e.renewal_period_value != null ? `${e.renewal_period_value} ${e.renewal_period_unit || ""}`.trim() : null) },
    { label: "Notice period", purpose: "notice_period", fmt: noticeText },
    { label: "Notice anchor", purpose: "notice_anchor",
      fmt: (e) => (e.notice_anchor_type ? (ANCHOR_LABEL[e.notice_anchor_type] || e.notice_anchor_type) : null) },
    { label: "Notice method", purpose: "notice_method", fmt: (e) => e.notice_method || null },
    { label: "Notice recipient", purpose: "notice_recipient", fmt: (e) => e.notice_recipient || null, eq: recipientUnchanged },
    { label: "Term ends", purpose: "renewal_term", fmt: (e) => longDate(e.current_term_end) },
    { label: "Renewal starts", purpose: "renewal_term", fmt: (e) => longDate(e.next_renewal_date) },
    { label: "Deadline", purpose: "notice_period", fmt: (e) => longDate(e.effective_action_deadline) },
  ],
  price_increase: [
    { label: "Increase type", purpose: "increase",
      fmt: (e) => INCREASE_TYPE_LABEL[e.increase_type] || e.increase_type || null },
    { label: "Rate", purpose: "increase",
      fmt: (e) => (e.increase_percent != null ? `${e.increase_percent}%`
        : e.increase_amount != null ? String(e.increase_amount) : null) },
    { label: "Effective from", purpose: "increase", fmt: (e) => longDate(e.price_change_date) },
    { label: "Objection window", purpose: "objection",
      fmt: (e) => (e.objection_window_value != null ? `${e.objection_window_value} ${e.objection_window_unit || "days"}` : null) },
    { label: "Deadline", purpose: "objection", fmt: (e) => longDate(e.effective_action_deadline) },
  ],
  termination_right: [
    { label: "Termination type", purpose: "termination_right",
      fmt: (e) => TERMINATION_TYPE_LABEL[e.termination_type] || e.termination_type || null },
    { label: "Notice period", purpose: "notice_period",
      fmt: (e) => (e.notice_period_value != null ? `${e.notice_period_value} ${e.notice_period_unit || "days"}` : null) },
    { label: "Earliest exit", purpose: "effective_timing", fmt: (e) => longDate(e.earliest_termination_date) },
    { label: "Termination fee", purpose: "termination_fee",
      fmt: (e) => (e.termination_fee_amount != null ? String(e.termination_fee_amount)
        : e.termination_fee_percent != null ? `${e.termination_fee_percent}%` : null) },
    { label: "Deadline", purpose: "notice_period", fmt: (e) => longDate(e.effective_action_deadline) },
  ],
  generic: [
    { label: "Who it applies to", purpose: "party", fmt: (e) => e.who || null },
    { label: "Amount", purpose: "amount",
      fmt: (e) => (e.amount != null ? String(e.amount)
        : e.amount_percent != null ? `${e.amount_percent}%` : e.rate_text || null) },
    { label: "Window", purpose: "window",
      fmt: (e) => (e.window_value != null ? `${e.window_value} ${e.window_unit || "days"}` : null) },
    { label: "Measured from", purpose: "window", fmt: (e) => e.window_reference || null },
    { label: "Deadline", purpose: "window", fmt: (e) => longDate(e.effective_action_deadline) },
  ],
};

function fieldDefsFor(type) {
  if (FIELD_DEFS[type]) return FIELD_DEFS[type];
  if (GENERIC_TYPES.includes(type)) return FIELD_DEFS.generic;
  return [];
}

export function buildAmendmentDiff(type, oldFinding, newFinding) {
  const defs = fieldDefsFor(type);
  const oldE = oldFinding?.extracted || {};
  const newE = newFinding?.extracted || {};
  const rows = [];
  for (const def of defs) {
    const before = def.fmt(oldE);
    const after = def.fmt(newE);
    if (before === after) continue;
    if (before == null && after == null) continue;
    if (def.eq && def.eq(before, after)) continue;
    rows.push({ label: def.label, before: before ?? "Not stated", after: after ?? "Not stated", purpose: def.purpose });
  }
  return rows;
}

function sourceFor(sources, purpose) {
  return (sources || []).find((s) => s.purpose === purpose) || null;
}

// Only the first changed field with BOTH a validated before AND after quote
// is used — never invents attribution for a row that lacks one side.
function pickEvidencePair(rows, oldFinding, newFinding) {
  for (const row of rows) {
    const before = sourceFor(oldFinding?.sources, row.purpose);
    const after = sourceFor(newFinding?.sources, row.purpose);
    if (before && after) return { before, after };
  }
  return null;
}

function QuoteBlock({ label, source, testid }) {
  const meta = source.document_metadata;
  return (
    <div className="bg-document rounded-sm p-4" data-testid={testid}>
      <p className="cc-eyebrow !text-document-soft">{label}</p>
      <p className="cc-clause mt-2">{source.quote}</p>
      <p className="cc-section-ref mt-2">
        {meta ? `${meta.filename} \u00b7 ${ROLE_LABEL[meta.doc_role] || meta.doc_role}` : "Source unresolved"}
        {source.location ? ` \u00b7 ${source.location}` : ""}
      </p>
    </div>
  );
}

export function AmendmentDiffDisclosure({ oldFinding, newFinding, type, mobile = false }) {
  const [open, setOpen] = useState(false);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const rows = buildAmendmentDiff(type, oldFinding, newFinding);
  if (!rows.length) return null;
  const evidence = pickEvidencePair(rows, oldFinding, newFinding);
  const tid = (name) => (mobile ? `${name}-mobile` : name);

  return (
    <div className="pt-3 border-t border-rule" data-testid={tid("amendment-diff-disclosure")}>
      <button
        onClick={() => setOpen((o) => !o)}
        data-testid={tid("amendment-diff-toggle")}
        className={`cc-section-ref flex items-center gap-1.5 text-ink hover:text-seal transition-colors bg-transparent border-0 p-0 cursor-pointer font-sans font-semibold ${mobile ? "text-xs" : ""}`}
      >
        Review amendment changes
        <ChevronDown className={`h-3.5 w-3.5 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="mt-3 space-y-2" data-testid={tid("amendment-diff-rows")}>
          {rows.map((r, i) => (
            <div key={i} className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5"
              data-testid={tid(`amendment-diff-row-${i}`)}>
              <span className={`cc-days-remaining text-ink-soft ${mobile ? "text-xs" : ""}`}>{r.label}</span>
              <span className={`cc-plain-english text-ink text-right font-medium ${mobile ? "text-xs" : "text-[15px]"}`}>
                {r.before} <span className="text-ink-soft">{"\u2192"}</span> {r.after}
              </span>
            </div>
          ))}

          {evidence && (
            <div className="pt-2">
              <button
                onClick={() => setEvidenceOpen((o) => !o)}
                data-testid={tid("amendment-evidence-toggle")}
                className={`cc-section-ref text-ink hover:text-seal transition-colors bg-transparent border-0 p-0 cursor-pointer font-sans font-semibold ${mobile ? "text-xs" : ""}`}
              >
                {evidenceOpen ? "Hide the evidence" : "Show the evidence"}
              </button>
              {evidenceOpen && (
                <div className="mt-3 grid gap-3 sm:grid-cols-2" data-testid={tid("amendment-evidence-panel")}>
                  <QuoteBlock label="Original clause" source={evidence.before} testid={tid("amendment-quote-before")} />
                  <QuoteBlock label="Amendment clause" source={evidence.after} testid={tid("amendment-quote-after")} />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
