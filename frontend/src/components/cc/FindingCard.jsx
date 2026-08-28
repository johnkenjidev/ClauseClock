// FindingCard — Stage 2 renewal_notice display + the signature clause drawer.
// Summary register (calm, white) with the hero deadline; evidence register
// (verbatim, --document ground) grouped by purpose with server-resolved
// source locations. No plain-English explanations (that is Stage 4).
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Check, Pencil, X, Bell, Trash2, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { LegalFooter, FindingBanner, BTN_TERTIARY } from "@/components/cc/Primitives";
import { CorrectFindingDialog } from "@/components/cc/CorrectFindingDialog";
import { AmendmentDiffDisclosure } from "@/components/cc/AmendmentDiff";

const STATE_BADGE = {
  confirmed: { label: "Confirmed", cls: "bg-seal text-paper" },
  corrected: { label: "Corrected", cls: "bg-seal text-paper" },
  dismissed: { label: "Dismissed", cls: "bg-card text-ink-soft border border-rule" },
};

const PURPOSE_LABEL = {
  effective_date: "Effective date",
  renewal_term: "Renewal term",
  notice_period: "Notice period",
  notice_method: "Notice method",
  notice_recipient: "Notice recipient",
  business_day_definition: "Business day definition",
  deemed_receipt: "Deemed receipt",
  notice_anchor: "Notice anchor",
  notice_anchor_prior: "Notice anchor — prior extraction (not applied)",
  value: "Contract value",
  increase: "Price increase",
  objection: "Objection window",
  increase_basis: "What it applies to",
  termination_right: "Termination right",
  effective_timing: "Effective timing",
  termination_fee: "Termination fee",
  obligation: "Clause",
  window: "Timing window",
  amount: "Amount",
  party: "Who it applies to",
  method: "Method",
};

const INCREASE_TYPE_LABEL = {
  fixed_automatic: "Fixed automatic",
  capped: "Capped (maximum)",
  formula: "Formula / index-linked",
  unspecified: "Unspecified",
};

const ANCHOR_LABEL = {
  term_end: "Term end",
  renewal_start: "Renewal start",
  unknown: "Unknown",
};
function anchorFactValue(e) {
  const base = ANCHOR_LABEL[e.notice_anchor_type] || e.notice_anchor_type;
  if (e.notice_anchor_origin === "user") return `${base} · set by you`;
  if (e.notice_anchor_origin === "document") return `${base} · from contract`;
  return base;
}

const MONTHS = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"];

function heroDate(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.split("-").map(Number);
  return `${MONTHS[m - 1]} ${d}`;
}
function longDate(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US",
    { year: "numeric", month: "long", day: "numeric" });
}
const money = (v, cur) =>
  v == null ? null : new Intl.NumberFormat("en-US",
    { style: "currency", currency: cur || "USD", maximumFractionDigits: 0 }).format(v);

// price_increase presentation helpers
function rateText(e) {
  if (e.increase_type === "formula") return e.increase_formula || "Formula (not stated)";
  if (e.increase_percent != null)
    return `${e.increase_percent}%${e.increase_type === "capped" ? " (max)" : ""}`;
  if (e.increase_amount != null) return money(e.increase_amount) || "Not stated";
  return "Not stated";
}
function objectionWindowText(e) {
  if (e.objection_window_value == null) return null;
  const unit = e.objection_window_unit || "days";
  const b = e.objection_basis === "business" ? " business" : "";
  return `${e.objection_window_value}${b} ${unit}`;
}
function priceHeadline(e) {
  if (e.increase_type === "formula") return (e.increase_formula || "FORMULA").toUpperCase();
  if (e.increase_type === "capped") return e.increase_percent != null ? `UP TO ${e.increase_percent}%` : "CAPPED";
  if (e.increase_percent != null) return `+${e.increase_percent}%`;
  if (e.increase_amount != null) return `+${money(e.increase_amount)}`;
  return "INCREASE";
}
function priceSubhead(e) {
  if (e.increase_type === "capped") return "Maximum permitted increase — not guaranteed.";
  if (e.increase_type === "formula") return "Amount depends on the external index at the time.";
  if (e.next_term_amount != null) return "Applies automatically at the next term.";
  return "Stated price increase.";
}

// termination_right presentation helpers
const TERMINATION_TYPE_LABEL = {
  for_convenience: "For convenience",
  early_exit: "Early exit / break right",
  for_cause: "For cause only",
  unspecified: "Unspecified",
};
function terminationHeadline(e) {
  return (TERMINATION_TYPE_LABEL[e.termination_type] || "Termination right").toUpperCase();
}
function noticePeriodText(e) {
  if (e.notice_period_value == null) return null;
  const unit = e.notice_period_unit || "days";
  const b = e.notice_basis === "business" ? " business" : "";
  return `${e.notice_period_value}${b} ${unit}`;
}
function terminationSubhead(e) {
  const np = noticePeriodText(e);
  if (e.termination_type === "for_cause") return "Exit permitted only on the stated cause.";
  if (np) return `Give ${np} notice to exit early.`;
  return "An early-exit right applies.";
}

// Stage 8/10 — shared obligation finding types.
const GENERIC_TYPES = [
  "service_credit", "invoice_dispute", "notice_requirement",
  "fee_or_penalty", "rebate_or_refund", "warranty_claim",
];
const GENERIC_LABEL = {
  service_credit: "Service credit",
  invoice_dispute: "Invoice dispute",
  notice_requirement: "Notice requirement",
  fee_or_penalty: "Fee or penalty",
  rebate_or_refund: "Rebate or refund",
  warranty_claim: "Warranty claim",
};
function genericWindowText(e) {
  if (e.window_value == null) return null;
  const unit = e.window_unit || "days";
  const b = e.window_basis === "business" ? " business" : "";
  return `${e.window_value}${b} ${unit}`;
}
function genericSubhead(f) {
  const e = f.extracted || {};
  const w = genericWindowText(e);
  if (w) return `Within ${w}${e.window_reference ? ` of ${e.window_reference}` : ""}.`;
  if (f.money_amount != null) return "A stated amount applies — see the details below.";
  return "See the cited contract language below.";
}
function genericMoneyLabel(type) {
  if (type === "fee_or_penalty") return "Fee / penalty";
  if (type === "service_credit") return "Service credit";
  if (type === "rebate_or_refund") return "Rebate / refund";
  return "Amount";
}

// Palette selection per PART 5: stamp only ≤14d AND action required; pending
// for 15–60d / review; neutral otherwise.
function tone(f) {
  if (f.validation_status === "needs_review") return "pending";
  const dr = f.extracted?.days_remaining;
  if (dr == null) return "neutral";
  if (dr <= 14 && f.action_required) return "stamp";
  if (dr <= 60) return "pending";
  return "neutral";
}
const TONE_TEXT = { stamp: "text-stamp", pending: "text-pending", neutral: "text-ink" };
const TONE_RULE = { stamp: "bg-stamp", pending: "bg-pending", neutral: "bg-seal" };
const RANK_LABEL = {
  urgent: "Urgent", money: "Money", risk: "Risk",
  opportunity: "Opportunity", informational: "Informational",
};

import { localDaysRemaining } from "@/lib/dates";

export function FindingCard({ finding, onChanged, readOnly = false, supersededRecord = null }) {
  const [open, setOpen] = useState(false);
  const [correctOpen, setCorrectOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [explanationOpen, setExplanationOpen] = useState(false);
  const e = finding.extracted || {};
  const navigate = useNavigate();
  const isPrice = finding.type === "price_increase";
  const isComposite = finding.type === "renewal_with_escalation";
  const isTermination = finding.type === "termination_right";
  const isGeneric = GENERIC_TYPES.includes(finding.type);
  const needsReview = finding.validation_status === "needs_review";
  const dr = localDaysRemaining(e.effective_action_deadline);
  const lapsed = dr != null && dr < 0;
  const t = needsReview
    ? "pending"
    : (dr != null && dr >= 0 && dr <= 14 && finding.action_required)
      ? "stamp"
      : (dr != null && dr >= 0 && dr <= 60)
        ? "pending"
        : "neutral";
  const badge = STATE_BADGE[finding.state];

  const act = async (verb) => {
    setBusy(true);
    try {
      const { data } = await api.post(`/findings/${finding.id}/${verb}`);
      onChanged?.(data.finding);
    } finally { setBusy(false); }
  };

  const grouped = {};
  for (const s of finding.sources || []) {
    (grouped[s.purpose] = grouped[s.purpose] || []).push(s);
  }
  // Presentation-level dedup: collapse rows with the same purpose + quote +
  // location (e.g. a "renewal_term" clause tagged for both the initial term
  // and the renewal period surfaces as one row, not two).
  for (const p of Object.keys(grouped)) {
    const seen = new Set();
    grouped[p] = grouped[p].filter((s) => {
      const key = `${(s.quote || "").trim()}|${String(s.document_id || "")}|${s.location || ""}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
  const orderedPurposes = Object.keys(PURPOSE_LABEL).filter((p) => grouped[p]);

  const noticeText = () => {
    if (e.notice_days_min == null) return "Not stated";
    const basis = e.notice_basis === "business" ? "business days" : "days";
    if (e.notice_days_max != null)
      return `${e.notice_days_min}–${e.notice_days_max} ${basis}`;
    return `${e.notice_days_min} ${basis}`;
  };

  const heroIso = e.effective_action_deadline;

  const urgent = dr != null && dr >= 0 && dr <= 14 && finding.action_required;

  return (
    <div data-testid={`finding-${finding.id}`}
      className="rounded-lg border border-rule bg-card overflow-hidden">
      
      {/* Desktop-only view */}
      <div className="hidden md:block p-6">
        <div className="flex items-start justify-between gap-6">
          <div>
            <p className="cc-eyebrow">{isComposite ? "Renewal + price increase" : isTermination ? "Termination right" : isGeneric ? GENERIC_LABEL[finding.type] : isPrice ? "Price increase" : "Automatic renewal"}</p>
            {finding.rank_category && (
              <span data-testid="finding-rank-category"
                className="inline-block cc-eyebrow mt-1 text-ink-soft">
                {RANK_LABEL[finding.rank_category]}
              </span>
            )}
            {needsReview ? (
              <>
                <p className={`cc-hero-date mt-3 ${TONE_TEXT[t]}`} data-testid="finding-needs-review">
                  NEEDS REVIEW
                </p>
                <p className="cc-days-remaining mt-2 max-w-md">
                  {finding.validation_notes?.[0] ||
                    "This finding needs review before a deadline can be shown."}
                </p>
              </>
            ) : isTermination ? (
              <>
                <p className={`cc-hero-date mt-3 ${TONE_TEXT[t]}`} data-testid="finding-termination-headline">
                  {terminationHeadline(e)}
                </p>
                <p className="cc-days-remaining mt-2 max-w-md" data-testid="finding-termination-subhead">
                  {terminationSubhead(e)}
                </p>
              </>
            ) : isPrice && !heroIso ? (
              <>
                <p className={`cc-hero-date mt-3 ${TONE_TEXT[t]}`} data-testid="finding-price-headline">
                  {priceHeadline(e)}
                </p>
                <p className="cc-days-remaining mt-2 max-w-md" data-testid="finding-price-subhead">
                  {priceSubhead(e)}
                </p>
              </>
            ) : isGeneric && !heroIso ? (
              <>
                <p className={`cc-hero-date mt-3 ${TONE_TEXT[t]}`} data-testid="finding-generic-headline">
                  {(GENERIC_LABEL[finding.type] || "Obligation").toUpperCase()}
                </p>
                <p className="cc-days-remaining mt-2 max-w-md" data-testid="finding-generic-subhead">
                  {genericSubhead(finding)}
                </p>
              </>
            ) : (
              <>
                <p className={`cc-hero-date mt-3 ${TONE_TEXT[t]}`} data-testid="finding-hero-date">
                  {heroDate(heroIso) || "—"}
                </p>
                <p className="cc-days-remaining mt-2" data-testid="finding-days-remaining">
                  {dr != null
                    ? dr < 0
                      ? `${Math.abs(dr)} day${Math.abs(dr) === 1 ? "" : "s"} past deadline`
                      : `${dr} day${dr === 1 ? "" : "s"} remaining`
                    : "Deadline not calculated"}
                </p>
              </>
            )}
          </div>
          <div className="text-right">
            {badge && (
              <span data-testid="finding-state-badge"
                className={`inline-block cc-eyebrow px-2.5 py-1 rounded-full mb-2 ${badge.cls}`}>
                {badge.label}
              </span>
            )}
            <p className="cc-eyebrow">Confidence</p>
            <p className={`cc-finding-title text-[16px] mt-1 capitalize ${TONE_TEXT[t]}`}
              data-testid="finding-confidence">{finding.confidence}</p>
          </div>
        </div>

        <div className={`mt-5 h-[3px] w-11 rounded ${TONE_RULE[t]}`} />

        {/* Legacy: computed before anchor classification. Keep deadline; mark for
            review. Reason-driven banner (reused for other reasons later). */}
        {finding.type === "renewal_notice" && finding.anchor_version == null && e.effective_action_deadline && (
          <FindingBanner tone="info" testid="finding-legacy-anchor-banner"
            message="Computed before anchor classification — review recommended." />
        )}

        {/* Key facts */}
        {isComposite ? (
          <dl className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
            <Fact label="Renews on"
              value={longDate(e.next_renewal_date) || "Not calculated"} testid="composite-next-renewal" />
            <Fact label="Increase type"
              value={INCREASE_TYPE_LABEL[e.increase_type] || "Not stated"} testid="composite-increase-type" />
            {e.increase_type === "fixed_automatic" && e.next_term_amount != null && (
              <>
                <Fact label="Next-term value"
                  value={<span className="cc-money">{money(e.next_term_amount, finding.money_currency)}</span>}
                  testid="composite-next-term-value" />
                <Fact label="Increase (delta)"
                  value={<span className="cc-money">+{money(e.escalation_delta, finding.money_currency)}</span>}
                  testid="composite-delta" />
              </>
            )}
            {e.increase_type === "capped" && (
              <Fact label="Maximum permitted"
                value={e.max_permitted_amount != null
                  ? <span className="cc-money">{money(e.max_permitted_amount, finding.money_currency)} <span className="text-ink-soft">(max, not guaranteed)</span></span>
                  : `Up to ${e.increase_percent}% (max, not guaranteed)`}
                testid="composite-max-permitted" />
            )}
            {e.increase_type === "formula" && (
              <Fact label="Escalation formula"
                value={e.increase_formula || "Formula (not stated)"} testid="composite-formula" />
            )}
            {e.effective_action_deadline && (
              <Fact label="Notice deadline"
                value={longDate(e.effective_action_deadline)} testid="composite-notice-deadline" />
            )}
          </dl>
        ) : isTermination ? (
          <dl className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
            <Fact label="Termination type"
              value={TERMINATION_TYPE_LABEL[e.termination_type] || "Not stated"} testid="finding-termination-type" />
            {e.who_may_terminate && (
              <Fact label="Who may terminate" value={e.who_may_terminate} testid="finding-termination-who" />
            )}
            <Fact label="Notice period"
              value={noticePeriodText(e) || "Not stated"} testid="finding-termination-notice" />
            {(e.cure_period_value != null) && (
              <Fact label="Cure period"
                value={`${e.cure_period_value} ${e.cure_period_unit || "days"}`} testid="finding-termination-cure" />
            )}
            {e.earliest_termination_date && (
              <Fact label="Earliest exit"
                value={longDate(e.earliest_termination_date)} testid="finding-termination-earliest" />
            )}
            {(e.termination_fee_amount != null || e.termination_fee_percent != null) && (
              <Fact label="Termination fee"
                value={e.termination_fee_amount != null
                  ? <span className="cc-money">{money(e.termination_fee_amount, finding.money_currency)}</span>
                  : `${e.termination_fee_percent}%`}
                testid="finding-termination-fee" />
            )}
            {e.method && (
              <Fact label="Notice method" value={e.method} testid="finding-termination-method" />
            )}
            {e.recipient && (
              <Fact label="Notice recipient" value={e.recipient} testid="finding-termination-recipient" />
            )}
          </dl>
        ) : isPrice ? (
          <dl className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
            <Fact label="Increase type"
              value={INCREASE_TYPE_LABEL[e.increase_type] || "Not stated"} testid="finding-increase-type" />
            <Fact label="Rate" value={rateText(e)} testid="finding-increase-rate" />
            {e.price_change_date && (
              <Fact label="Effective from" value={longDate(e.price_change_date)} testid="finding-price-change-date" />
            )}
            {e.next_term_amount != null && (
              <Fact label="Next-term value"
                value={<span className="cc-money">{money(e.next_term_amount, finding.money_currency)}</span>}
                testid="finding-next-term-amount" />
            )}
            {e.max_permitted_amount != null && (
              <Fact label="Maximum permitted"
                value={<span className="cc-money">{money(e.max_permitted_amount, finding.money_currency)}</span>}
                testid="finding-max-permitted" />
            )}
            {objectionWindowText(e) && (
              <Fact label="Objection window" value={objectionWindowText(e)} testid="finding-objection-window" />
            )}
            {!needsReview && e.objection_deadline && (
              <Fact label="Objection deadline" value={longDate(e.objection_deadline)} testid="finding-objection-deadline" />
            )}
            {e.increase_basis && (
              <Fact label="Applies to" value={e.increase_basis} testid="finding-increase-basis" />
            )}
            {finding.money_amount != null && (
              <Fact label={e.increase_type === "capped" ? "Maximum annual increase" : "Estimated annual increase"}
                value={<span className="cc-money">{money(finding.money_amount, finding.money_currency)}</span>}
                testid="finding-money" />
            )}
          </dl>
        ) : isGeneric ? (
          <dl className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
            <Fact label="Type" value={GENERIC_LABEL[finding.type]} testid="finding-generic-type" />
            {e.who && (
              <Fact label="Who it applies to" value={e.who} testid="finding-generic-who" />
            )}
            {finding.money_amount != null && (
              <Fact label={genericMoneyLabel(finding.type)}
                value={<span className="cc-money">{money(finding.money_amount, finding.money_currency)}</span>}
                testid="finding-generic-amount" />
            )}
            {e.amount_percent != null && (
              <Fact label="Percentage" value={`${e.amount_percent}%`} testid="finding-generic-percent" />
            )}
            {e.rate_text && (
              <Fact label="Rate" value={e.rate_text} testid="finding-generic-rate" />
            )}
            {genericWindowText(e) && (
              <Fact label="Window" value={genericWindowText(e)} testid="finding-generic-window" />
            )}
            {e.window_reference && (
              <Fact label="Measured from" value={e.window_reference} testid="finding-generic-reference" />
            )}
            {!needsReview && e.effective_action_deadline && (
              <Fact label="Deadline" value={longDate(e.effective_action_deadline)} testid="finding-generic-deadline" />
            )}
          </dl>
        ) : (
          <dl className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
            <Fact label="Next renewal"
              value={longDate(e.next_renewal_date) || "Not calculated"} testid="finding-next-renewal" />
            <Fact label="Notice period" value={noticeText()} testid="finding-notice-period" />
            {e.notice_anchor_type && (
              <Fact label="Notice counts back from" value={anchorFactValue(e)} testid="finding-notice-anchor" />
            )}
            {!needsReview && e.earliest_action_date && (
              <Fact label="Notice window"
                value={`${longDate(e.earliest_action_date)} – ${longDate(e.effective_action_deadline)}`}
                testid="finding-notice-window" />
            )}
            <Fact label="Notice method" value={e.notice_method || "Not stated"} testid="finding-notice-method" />
            <Fact label="Notice recipient" value={e.notice_recipient || "Not stated"} testid="finding-notice-recipient" />
            {finding.money_amount != null && (
              <Fact label="Contract value"
                value={<span className="cc-money">{money(finding.money_amount, finding.money_currency)}</span>}
                testid="finding-money" />
            )}
          </dl>
        )}

        {finding.validation_notes?.length > 0 && (
          <ul className="mt-5 space-y-1">
            {finding.validation_notes.map((n, i) => (
              <li key={i} className="cc-days-remaining text-pending" data-testid="finding-note">• {n}</li>
            ))}
          </ul>
        )}

        {/* Stage 4 explanation — derived ONLY from the validated clauses below.
            Never shown for needs_review; the clause drawer remains the evidence. */}
        {!needsReview && finding.plain_english && (
          <div className="mt-6 rounded-md border border-rule bg-card p-5" data-testid="finding-explanation">
            <p className="cc-eyebrow">In plain English</p>
            <p className="cc-plain-english mt-2" data-testid="finding-plain-english">{finding.plain_english}</p>
            {finding.why_it_matters && (
              <>
                <p className="cc-eyebrow mt-4">Why it matters</p>
                <p className="cc-plain-english mt-2" data-testid="finding-why">{finding.why_it_matters}</p>
              </>
            )}
            {finding.suggested_action && !lapsed && (
              <>
                <p className="cc-eyebrow mt-4">Suggested action</p>
                <p className="cc-plain-english mt-2" data-testid="finding-suggested-action">{finding.suggested_action}</p>
              </>
            )}
            <p className="cc-section-ref mt-4 text-ink-soft">
              Summarised from the cited clauses below — verify against the original contract.
            </p>
          </div>
        )}

        {dr != null && dr < 0 && finding.type === "renewal_notice" && (
          <div className="mt-6 p-4 rounded-md border border-rule bg-card/60 text-ink-soft text-sm font-sans" data-testid="lapsed-disclaimer">
            Non-renewal window elapsed. This deadline can no longer be met under the cited clause. Contract is scheduled to renew {longDate(e.next_renewal_date)}.
          </div>
        )}

        {/* Stage 3 actions — CTA respects state (Part 5) */}
        {!readOnly && (
        <div className="mt-6">
          {finding.state === "unconfirmed" && (
            <p className="cc-days-remaining mb-3 max-w-xl" data-testid="finding-confirm-hint">
              ClauseClock won’t track this deadline until you’ve checked it against the source clause.
            </p>
          )}
          <div className="flex flex-wrap items-center gap-2">
          {finding.state === "unconfirmed" ? (
            <Button size="sm" disabled={busy} data-testid="finding-confirm-btn"
              onClick={() => act("confirm")}
              className="bg-seal text-paper hover:bg-seal/90 rounded-full h-9 px-4 gap-1.5 font-semibold">
              <Check className="h-4 w-4" strokeWidth={2.5} /> Confirm deadline
            </Button>
          ) : (finding.action_required && (dr === null || dr >= 0)) ? (
            <Button size="sm" data-testid="finding-prepare-notice-btn"
              onClick={() => navigate("/app/action-center")}
              className="bg-seal text-paper hover:bg-seal/90 rounded-full h-9 px-4 gap-1.5 font-semibold">
              <Check className="h-4 w-4" strokeWidth={2.5} /> Prepare notice
            </Button>
          ) : (
            <span className="inline-flex items-center gap-2 cc-days-remaining text-seal" data-testid="finding-confirmed-badge">
              <span className="h-1.5 w-1.5 rounded-full bg-seal" /> Confirmed
            </span>
          )}
          <Button size="sm" variant="outline" disabled={busy} data-testid="finding-correct-btn"
            onClick={() => setCorrectOpen(true)}
            className={`rounded-full h-9 px-4 gap-1.5 border-rule text-ink hover:text-ink hover:border-ink-soft hover:bg-card font-semibold ${isComposite ? "hidden" : ""}`}>
            <Pencil className="h-4 w-4" strokeWidth={2} /> Correct
          </Button>
          <Button size="sm" variant="ghost" disabled={busy} data-testid="finding-dismiss-btn"
            onClick={() => act("dismiss")}
            className="rounded-full h-9 px-4 gap-1.5 text-ink-soft hover:text-ink hover:bg-card font-semibold">
            <X className="h-4 w-4" strokeWidth={2} /> Dismiss
          </Button>
          </div>
        </div>
        )}

        {!readOnly && !needsReview && heroIso && !lapsed && (
          <RemindersBlock findingId={finding.id} deadline={heroIso} />
        )}

        {supersededRecord && (
          <AmendmentDiffDisclosure oldFinding={supersededRecord} newFinding={finding} type={finding.type} />
        )}

        {/* Clause drawer toggle */}
        <button
          data-testid="clause-drawer-toggle"
          onClick={() => setOpen((o) => !o)}
          className={`mt-6 ${BTN_TERTIARY} transition-colors`}>
          <span>{open ? "Hide the contract language" : "Show the contract language"}</span>
          <ChevronDown className={`h-3.5 w-3.5 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
        </button>
      </div>

      {/* Mobile-only view */}
      <div className="md:hidden p-5 space-y-4">
        {/* Finding header / type */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="cc-eyebrow font-sans text-ink-soft">
              {isComposite ? "Renewal + price increase" : isTermination ? "Termination right" : isGeneric ? GENERIC_LABEL[finding.type] : isPrice ? "Price increase" : "Automatic renewal"}
            </p>
            {finding.rank_category && (
              <span className="text-xs font-sans text-ink-soft mt-1 block">
                {RANK_LABEL[finding.rank_category]}
              </span>
            )}
          </div>
          
          {/* Neutral confidence block */}
          <div className="text-right">
            <span className="text-xs font-sans text-ink-soft uppercase tracking-wider">Confidence</span>
            <p className="text-sm font-sans text-ink font-semibold mt-0.5 capitalize">{finding.confidence}</p>
          </div>
        </div>

        {/* 1. Urgent finding alert (stamp red only if <= 14d and action required) */}
        {urgent && dr != null && dr >= 0 && (
          <div className="bg-stamp/5 border border-stamp/30 p-3 flex items-start gap-2.5 rounded-sm">
            <AlertTriangle className="h-4 w-4 text-stamp mt-0.5 shrink-0" strokeWidth={2.5} />
            <p className="text-xs font-sans text-stamp font-semibold leading-relaxed">
              Urgent action required · {dr} days remaining to give notice.
            </p>
          </div>
        )}

        {/* 2. Deadline state + factual consequence */}
        <div className="pt-2 border-t border-rule space-y-3">
          {needsReview ? (
            <>
              <p className="text-sm font-sans font-semibold text-ink" data-testid="finding-needs-review-mobile">NEEDS REVIEW</p>
              <p className="text-xs font-sans text-ink-soft leading-relaxed">
                {finding.validation_notes?.[0] || "This finding needs review before a deadline can be shown."}
              </p>
            </>
          ) : isTermination ? (
            <>
              <p className="text-sm font-sans font-semibold text-ink" data-testid="finding-termination-headline-mobile">{terminationHeadline(e)}</p>
              <p className="text-xs font-sans text-ink-soft leading-relaxed" data-testid="finding-termination-subhead-mobile">{terminationSubhead(e)}</p>
            </>
          ) : isPrice && !heroIso ? (
            <>
              <p className="text-sm font-sans font-semibold text-ink" data-testid="finding-price-headline-mobile">{priceHeadline(e)}</p>
              <p className="text-xs font-sans text-ink-soft leading-relaxed" data-testid="finding-price-subhead-mobile">{priceSubhead(e)}</p>
            </>
          ) : isGeneric && !heroIso ? (
            <>
              <p className="text-sm font-sans font-semibold text-ink" data-testid="finding-generic-headline-mobile">{(GENERIC_LABEL[finding.type] || "Obligation").toUpperCase()}</p>
              <p className="text-xs font-sans text-ink-soft leading-relaxed" data-testid="finding-generic-subhead-mobile">{genericSubhead(finding)}</p>
            </>
          ) : (
            <>
              <p className="text-lg font-sans font-bold text-ink" data-testid="finding-hero-date-mobile">{heroDate(heroIso) || "—"}</p>
              <p className="text-xs font-sans text-ink-soft" data-testid="finding-days-remaining-mobile">
                {dr != null
                  ? dr < 0
                    ? `${Math.abs(dr)} day${Math.abs(dr) === 1 ? "" : "s"} past deadline`
                    : `${dr} day${dr === 1 ? "" : "s"} remaining`
                  : "Deadline not calculated"}
              </p>
            </>
          )}

          {lapsed && finding.type === "renewal_notice" && (
            <div className="p-3 rounded-sm border border-rule bg-card/60 text-ink-soft text-xs font-sans leading-relaxed" data-testid="lapsed-disclaimer-mobile">
              Non-renewal window elapsed. This deadline can no longer be met under the cited clause. Contract is scheduled to renew {longDate(e.next_renewal_date)}.
            </div>
          )}

          {/* Confirm / Correct / Dismiss */}
          {!readOnly && (
            <div className="pt-1 flex flex-wrap items-center gap-2">
              {finding.state === "unconfirmed" ? (
                <Button size="sm" disabled={busy} data-testid="finding-confirm-btn-mobile" onClick={() => act("confirm")} className="bg-seal text-paper hover:bg-seal/90 rounded-full h-8 px-4 font-semibold font-sans text-xs">
                  Confirm deadline
                </Button>
              ) : (finding.action_required && (dr === null || dr >= 0)) ? (
                <Button size="sm" data-testid="finding-prepare-notice-btn-mobile" onClick={() => navigate("/app/action-center")} className="bg-seal text-paper hover:bg-seal/90 rounded-full h-8 px-4 font-semibold font-sans text-xs">
                  Prepare notice
                </Button>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-xs text-seal font-semibold font-sans" data-testid="finding-confirmed-badge-mobile">
                  <span className="h-1.5 w-1.5 rounded-full bg-seal" /> Confirmed
                </span>
              )}
              {!isComposite && (
                <button data-testid="finding-correct-btn-mobile" disabled={busy} onClick={() => setCorrectOpen(true)}
                  className="border border-rule text-ink hover:border-ink-soft hover:bg-card rounded-full h-8 px-3 text-xs bg-transparent font-sans font-semibold cursor-pointer transition-colors">
                  Correct
                </button>
              )}
              <button data-testid="finding-dismiss-btn-mobile" disabled={busy} onClick={() => act("dismiss")}
                className="text-ink-soft hover:text-ink hover:underline text-xs bg-transparent border-0 p-0 font-sans font-semibold cursor-pointer">
                Dismiss
              </button>
            </div>
          )}
        </div>

        {/* Amendment-diff disclosure, when this finding replaces a preserved reviewed one */}
        {supersededRecord && (
          <AmendmentDiffDisclosure oldFinding={supersededRecord} newFinding={finding} type={finding.type} mobile />
        )}

        {/* 3. Concise visible explanation with disclosure */}
        {!needsReview && finding.plain_english && (
          <div className="bg-card border border-rule p-4 rounded-sm space-y-3">
            <span className="cc-eyebrow font-sans">Explanation</span>
            <p className="cc-plain-english text-xs text-ink leading-relaxed mt-1 font-sans">{finding.plain_english}</p>
            
            {(finding.why_it_matters || (finding.suggested_action && !lapsed)) && (
              <div className="pt-1">
                <button 
                  onClick={() => setExplanationOpen(!explanationOpen)} 
                  className="inline-flex items-center gap-1.5 text-xs text-ink-soft hover:text-ink font-sans font-semibold bg-transparent border-0 p-0 cursor-pointer transition-colors"
                >
                  <span>{explanationOpen ? "Hide explanation details" : "Show explanation details"}</span>
                  <ChevronDown className={`h-3.5 w-3.5 transition-transform duration-200 ${explanationOpen ? "rotate-180" : ""}`} />
                </button>
                
                {explanationOpen && (
                  <div className="mt-3 space-y-3 pt-3 border-t border-rule/50">
                    {finding.why_it_matters && (
                      <div>
                        <span className="text-[10px] text-ink-soft font-bold uppercase tracking-wider font-sans">Why it matters</span>
                        <p className="text-xs text-ink mt-0.5 leading-relaxed font-sans">{finding.why_it_matters}</p>
                      </div>
                    )}
                    {finding.suggested_action && !lapsed && (
                      <div>
                        <span className="text-[10px] text-ink-soft font-bold uppercase tracking-wider font-sans">Suggested action</span>
                        <p className="text-xs text-ink mt-0.5 leading-relaxed font-sans">{finding.suggested_action}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* 4. Collapsible Verbatim contract sources drawer toggle button */}
        <div className="pt-2 border-t border-rule">
          <button
            onClick={() => setOpen((o) => !o)}
            data-testid="clause-drawer-toggle-mobile"
            className={`${BTN_TERTIARY} transition-colors text-xs`}
          >
            <span>{open ? "Hide contract language" : "Show contract language"}</span>
            <ChevronDown className={`h-3.5 w-3.5 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
          </button>
        </div>

        {/* 5. Reminders Block (placed correctly after evidence toggle on mobile) */}
        {!readOnly && !needsReview && heroIso && !lapsed && (
          <div className="pt-2 border-t border-rule">
            <RemindersBlock findingId={finding.id} deadline={heroIso} />
          </div>
        )}
      </div>

      {/* The signature clause drawer — evidence register on --document ground */}
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            data-testid="clause-drawer"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: "easeOut" }}
            className="bg-document border-t border-rule overflow-hidden">
            <div className="px-6 py-6 space-y-6">
              {orderedPurposes.map((purpose) =>
                grouped[purpose].map((s, i) => (
                  <div key={`${purpose}-${i}`} data-testid={`clause-${purpose}`}>
                    <div className="flex items-baseline justify-between gap-4">
                      <span className="cc-eyebrow !text-document-soft">{PURPOSE_LABEL[purpose]}</span>
                      <span className="cc-section-ref">{s.location}</span>
                    </div>
                    <p className="cc-clause mt-2">{s.quote}</p>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Removed FindingCard local disclaimer block */}

      <CorrectFindingDialog finding={finding} open={correctOpen}
        onOpenChange={setCorrectOpen} onSaved={(f) => onChanged?.(f)} />
    </div>
  );
}

const Fact = ({ label, value, testid }) => (
  <div>
    <dt className="cc-eyebrow">{label}</dt>
    <dd className="cc-plain-english mt-1 text-ink" data-testid={testid}>{value}</dd>
  </div>
);

function RemindersBlock({ findingId, deadline }) {
  const [reminders, setReminders] = useState([]);
  const [days, setDays] = useState(30);
  const [busy, setBusy] = useState(false);
  const load = () =>
    api.get(`/findings/${findingId}/reminders`).then((r) => setReminders(r.data.reminders)).catch(() => {});
  useEffect(() => { load(); }, [findingId]);

  const add = async () => {
    setBusy(true);
    try { await api.post(`/findings/${findingId}/reminders`, { days_before: Number(days) }); load(); }
    finally { setBusy(false); }
  };
  const remove = async (id) => { await api.delete(`/reminders/${id}`); load(); };

  return (
    <div className="mt-6 pt-5 border-t border-rule" data-testid="reminders-block">
      <div className="flex items-center gap-2">
        <Bell className="h-4 w-4 text-ink-soft" strokeWidth={2} />
        <span className="cc-eyebrow">Deadline reminders</span>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="cc-days-remaining">Remind me</span>
        <input type="number" min="0" value={days} data-testid="reminder-days-input"
          onChange={(e) => setDays(e.target.value)}
          className="bg-card border border-rule rounded-md h-9 w-20 px-2 cc-days-remaining" />
        <span className="cc-days-remaining">days before the deadline</span>
        <Button size="sm" disabled={busy || days === "" } data-testid="reminder-add-btn" onClick={add}
          className="bg-seal text-paper hover:bg-seal/90 rounded-full h-9 px-4 font-semibold">
          {busy ? "Saving…" : "Set reminder"}
        </Button>
      </div>
      {reminders.length > 0 && (
        <ul className="mt-3 space-y-2" data-testid="reminders-list">
          {reminders.map((r) => {
            const isPast = new Date(r.fire_date) < new Date();
            return (
              <li key={r.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 rounded-md border border-rule bg-card px-4 py-2">
                <span className="cc-days-remaining text-ink font-sans text-xs break-words min-w-0" data-testid={`reminder-${r.id}`}>
                  {r.days_before} days before · {isPast ? `reminder date passed ${longDate(r.fire_date)}` : `fires ${longDate(r.fire_date)}`}
                </span>
                <button data-testid={`reminder-delete-${r.id}`} onClick={() => remove(r.id)}
                  className="text-ink-soft hover:text-stamp shrink-0 self-end sm:self-auto"><Trash2 className="h-4 w-4" /></button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
