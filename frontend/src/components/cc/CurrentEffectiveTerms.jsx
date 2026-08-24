// Current Effective Terms — the contract's factual ledger. Built ONLY from
// already-stored fields on the active (non-superseded) renewal_notice
// finding + contract-level annual value provenance. No new calculations,
// no re-extraction. Typography on the ground — no card/paper surface.
import { Eyebrow } from "@/components/cc/Primitives";

const ANCHOR_LABEL = { term_end: "Term end", renewal_start: "Renewal start", unknown: "Unknown" };

function longDate(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US",
    { year: "numeric", month: "long", day: "numeric" });
}
const money = (v, cur) =>
  v == null ? null : new Intl.NumberFormat("en-US",
    { style: "currency", currency: cur || "USD", maximumFractionDigits: 0 }).format(v);

function noticeText(e) {
  if (e.notice_days_min == null) return "Not stated";
  const basis = e.notice_basis === "business" ? "business days" : "days";
  return e.notice_days_max != null
    ? `${e.notice_days_min}\u2013${e.notice_days_max} ${basis}`
    : `${e.notice_days_min} ${basis}`;
}

// Governing source filename for a row — resolved from the finding's own
// validated sources ONLY. No guessing: absent purpose -> no label.
function sourceFilename(sources, purpose) {
  const s = (sources || []).find((x) => x.purpose === purpose);
  return s?.document_metadata?.filename || null;
}

export function CurrentEffectiveTerms({ finding, contract, documents, hasPendingAmendment, mobile = false }) {
  if (!finding) return null;
  const e = finding.extracted || {};
  const sources = finding.sources || [];
  const tid = (name) => (mobile ? `${name}-mobile` : name);

  const rows = [
    { label: "Current term ends", value: longDate(e.current_term_end) || "Not calculated", purpose: "renewal_term" },
    { label: "Renewal starts", value: longDate(e.next_renewal_date) || "Not calculated", purpose: "renewal_term" },
    { label: "Non-renewal notice period", value: noticeText(e), purpose: "notice_period" },
    { label: "Notice anchor", value: e.notice_anchor_type ? (ANCHOR_LABEL[e.notice_anchor_type] || e.notice_anchor_type) : "Not stated", purpose: "notice_anchor" },
    { label: "Current deadline", value: longDate(e.effective_action_deadline) || "Not calculated", purpose: "notice_period" },
    { label: "Notice method", value: e.notice_method || "Not stated", purpose: "notice_method" },
    { label: "Notice recipient", value: e.notice_recipient || "Not stated", purpose: "notice_recipient" },
  ];

  const annualValueDoc = contract.value_source === "extracted" && contract.value_source_document_id
    ? (documents || []).find((d) => d.id === contract.value_source_document_id)
    : null;

  return (
    <div className="space-y-3" data-testid={tid("current-effective-terms")}>
      <Eyebrow className="font-sans">Current effective terms</Eyebrow>
      <dl className="space-y-2.5">
        {rows.map((r, i) => {
          const src = sourceFilename(sources, r.purpose);
          return (
            <div key={i} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5"
              data-testid={tid(`cet-row-${i}`)}>
              <dt className={`cc-days-remaining text-ink-soft ${mobile ? "text-xs" : "text-sm"}`}>{r.label}</dt>
              <dd className={`cc-plain-english text-ink text-right flex items-baseline gap-2 flex-wrap justify-end ${mobile ? "text-xs" : "text-[15px]"}`}>
                <span>{r.value}</span>
                {src && <span className="cc-section-ref" data-testid={tid(`cet-source-${i}`)}>{src}</span>}
              </dd>
            </div>
          );
        })}
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5" data-testid={tid("cet-row-annual-value")}>
          <dt className={`cc-days-remaining text-ink-soft ${mobile ? "text-xs" : "text-sm"}`}>Annual value</dt>
          <dd className={`cc-plain-english text-ink text-right flex items-baseline gap-2 flex-wrap justify-end ${mobile ? "text-xs" : "text-[15px]"}`}>
            <span className="cc-money">
              {contract.annual_value != null ? money(contract.annual_value, contract.currency) : "Not provided"}
            </span>
            {annualValueDoc && <span className="cc-section-ref">{annualValueDoc.filename}</span>}
            {!annualValueDoc && contract.value_source === "user_entered" && (
              <span className="cc-section-ref">entered by you</span>
            )}
          </dd>
        </div>
      </dl>
      {hasPendingAmendment && (
        <p className={`cc-days-remaining text-ink-soft ${mobile ? "text-xs" : "text-sm"} pt-1`}
          data-testid={tid("cet-pending-amendment-note")}>
          Latest amendment changes are awaiting your review.
        </p>
      )}
    </div>
  );
}
